sim = require('sim')

-- EvalBridge simulation script scaffold.
--
-- Attach this script to a CoppeliaSim script object whose alias is "EvalBridge".
-- The Python evaluator resolves it via the absolute scene path "/EvalBridge".
--
-- This scaffold exports the functions expected by eval/run.py:
--   reset_episode(seed)
--   read_state()
--   apply_control(vx, vy, vz)
--
-- Replace the object paths below so they match your scene. This smoke-test
-- configuration moves a kinematic dummy at reduced speed, lifts it into the
-- air, and routes it through intermediate staged goals before the final goal.

local CONFIG = {
    drone_root_path = '/Drone',
    state_object_path = '/Drone',
    control_object_path = '/Drone',
    goal_object_path = '/Goal',
    collision_entity_path = nil,
    command_mode = 'kinematic_position', -- 'scene_specific' or 'kinematic_position'
    reset_dynamic_root = false,
    speed_scale = 0.10,
    route_mode = 'zigzag_steps', -- 'none', 'axis_steps', 'zigzag_steps', or 'custom_waypoints'
    route_lift_height_m = 0.5,
    route_turn_count = 6,
    route_turn_offset_m = 0.35,
    route_waypoint_tolerance_m = 0.10,
    move_goal_object_to_active_route_target = true,
    custom_route_waypoints = {
        -- Used only when route_mode = 'custom_waypoints'.
        -- Waypoints are absolute world positions. The final goal is appended
        -- automatically if it is not already the last waypoint.
        -- Example: {-0.5, 0.6, 0.0},
    },
    goal_tolerance_m = 0.15,
    max_linear_speed_mps = 2.0,
    start_position_jitter_m = {0.0, 0.0, 0.0},
    goal_position_jitter_m = {0.0, 0.0, 0.0},
}

local handles = {
    drone_root = -1,
    state_object = -1,
    control_object = -1,
    goal_object = -1,
    drone_collection = -1,
    collision_entity = -1,
}

local runtime = {
    initialized = false,
    episode_seed = 0,
    pending_command = {0.0, 0.0, 0.0},
    collision_count = 0,
    collision_active = false,
    error_code = nil,
    base_state_position = nil,
    base_state_orientation = nil,
    base_control_position = nil,
    base_goal_position = nil,
    final_goal_position = nil,
    route_targets = {},
    active_route_index = 1,
}

local function copyVector(v)
    return {v[1], v[2], v[3]}
end

local function scaleVector(v, scale)
    return {v[1] * scale, v[2] * scale, v[3] * scale}
end

local function clamp(value, min_value, max_value)
    return math.max(min_value, math.min(max_value, value))
end

local function distance(a, b)
    local dx = a[1] - b[1]
    local dy = a[2] - b[2]
    local dz = a[3] - b[3]
    return math.sqrt(dx * dx + dy * dy + dz * dz)
end

local function sameTarget(a, b)
    return distance(a, b) <= 0.001
end

local function maybeGetObject(path)
    if path == nil or path == '' then
        return -1
    end
    return sim.getObject(path, {noError = true})
end

local function requireObject(path, label)
    local handle = maybeGetObject(path)
    if handle == -1 then
        error(label .. ' not found: ' .. path)
    end
    return handle
end

local function sampleJitter(component_amplitude)
    if component_amplitude == 0.0 then
        return 0.0
    end
    return (math.random() * 2.0 - 1.0) * component_amplitude
end

local function withJitter(base_vec, jitter_vec)
    return {
        base_vec[1] + sampleJitter(jitter_vec[1]),
        base_vec[2] + sampleJitter(jitter_vec[2]),
        base_vec[3] + sampleJitter(jitter_vec[3]),
    }
end

local function appendTarget(targets, target)
    if #targets == 0 or not sameTarget(targets[#targets], target) then
        table.insert(targets, copyVector(target))
    end
end

local function buildRouteTargets(start_position, final_goal_position)
    local targets = {}
    local flight_z = start_position[3] + CONFIG.route_lift_height_m
    local dx = final_goal_position[1] - start_position[1]
    local dy = final_goal_position[2] - start_position[2]
    local horizontal_distance = math.sqrt(dx * dx + dy * dy)
    local routed_final_goal_position = {
        final_goal_position[1],
        final_goal_position[2],
        flight_z,
    }

    if CONFIG.route_lift_height_m ~= 0.0 then
        -- First lift vertically so the object visibly floats before it starts
        -- horizontal movement.
        appendTarget(targets, {start_position[1], start_position[2], flight_z})
    end

    if CONFIG.route_mode == 'custom_waypoints' then
        for _, waypoint in ipairs(CONFIG.custom_route_waypoints) do
            appendTarget(targets, waypoint)
        end
        appendTarget(targets, routed_final_goal_position)
        return targets
    end

    if CONFIG.route_mode == 'zigzag_steps' then
        if horizontal_distance > 0.001 then
            local perp_x = -dy / horizontal_distance
            local perp_y = dx / horizontal_distance
            for i = 1, CONFIG.route_turn_count do
                local progress = i / (CONFIG.route_turn_count + 1)
                local side = 1.0
                if i % 2 == 0 then
                    side = -1.0
                end
                appendTarget(targets, {
                    start_position[1] + dx * progress + perp_x * CONFIG.route_turn_offset_m * side,
                    start_position[2] + dy * progress + perp_y * CONFIG.route_turn_offset_m * side,
                    flight_z,
                })
            end
        end
        appendTarget(targets, routed_final_goal_position)
        return targets
    end

    if CONFIG.route_mode == 'axis_steps' then
        -- Move in staged segments: first align X, then align Y/Z, then finish.
        appendTarget(targets, {final_goal_position[1], start_position[2], flight_z})
        appendTarget(targets, {
            final_goal_position[1],
            final_goal_position[2],
            flight_z,
        })
        appendTarget(targets, routed_final_goal_position)
        return targets
    end

    appendTarget(targets, routed_final_goal_position)
    return targets
end

local function getActiveRouteTarget()
    if #runtime.route_targets == 0 then
        return runtime.final_goal_position
    end
    return runtime.route_targets[runtime.active_route_index]
end

local function getRoutePhase()
    local route_count = #runtime.route_targets
    if route_count == 0 then
        return 'uninitialized'
    end
    if runtime.active_route_index >= route_count then
        return 'final'
    end
    if CONFIG.route_mode == 'axis_steps' then
        if runtime.active_route_index == 1 then
            return 'lift'
        end
        if runtime.active_route_index == 2 then
            return 'move_x'
        end
        if runtime.active_route_index == 3 then
            return 'move_y'
        end
    end
    if CONFIG.route_mode == 'zigzag_steps' then
        if runtime.active_route_index == 1 and CONFIG.route_lift_height_m ~= 0.0 then
            return 'lift'
        end
        local turn_index = runtime.active_route_index
        if CONFIG.route_lift_height_m ~= 0.0 then
            turn_index = turn_index - 1
        end
        return string.format('turn_%02d', turn_index)
    end
    return CONFIG.route_mode
end

local function moveVisibleGoalToActiveTarget()
    if CONFIG.move_goal_object_to_active_route_target then
        sim.setObjectPosition(handles.goal_object, getActiveRouteTarget(), sim.handle_world)
    end
end

local function updateRouteProgress(position)
    while runtime.active_route_index < #runtime.route_targets do
        local active_target = getActiveRouteTarget()
        if distance(position, active_target) > CONFIG.route_waypoint_tolerance_m then
            break
        end
        runtime.active_route_index = runtime.active_route_index + 1
        moveVisibleGoalToActiveTarget()
    end
end

local function resetDynamicState()
    if CONFIG.reset_dynamic_root and handles.drone_root ~= -1 then
        sim.resetDynamicObject(handles.drone_root)
    end
end

local function applyCommandSceneSpecific(command)
    -- TODO: Replace this with actuator-specific control for your scene.
    -- Examples:
    --   * set target velocities on propeller joints
    --   * write signals consumed by another simulation script
    --   * move a target dummy that a low-level controller follows
    -- Returning without action is intentional until you wire the scene.
end

local function applyCommandKinematically(command)
    local dt = sim.getSimulationTimeStep()
    local current = sim.getObjectPosition(handles.control_object, sim.handle_world)
    local next_pos = {
        current[1] + command[1] * CONFIG.speed_scale * dt,
        current[2] + command[2] * CONFIG.speed_scale * dt,
        current[3] + command[3] * CONFIG.speed_scale * dt,
    }
    sim.setObjectPosition(handles.control_object, next_pos, sim.handle_world)
end

local function applyPendingCommand()
    if CONFIG.command_mode == 'kinematic_position' then
        applyCommandKinematically(runtime.pending_command)
        return
    end
    applyCommandSceneSpecific(runtime.pending_command)
end

local function updateCollisionState()
    if handles.drone_collection == -1 or handles.collision_entity == -1 then
        runtime.collision_active = false
        return
    end

    local result = sim.checkCollision(handles.drone_collection, handles.collision_entity)
    local collision_now = result > 0
    if collision_now and not runtime.collision_active then
        runtime.collision_count = runtime.collision_count + 1
    end
    runtime.collision_active = collision_now
end

local function resolveHandles()
    handles.drone_root = requireObject(CONFIG.drone_root_path, 'drone_root_path')
    handles.state_object = requireObject(CONFIG.state_object_path, 'state_object_path')
    handles.control_object = requireObject(CONFIG.control_object_path, 'control_object_path')
    handles.goal_object = requireObject(CONFIG.goal_object_path, 'goal_object_path')

    if CONFIG.collision_entity_path ~= nil and CONFIG.collision_entity_path ~= '' then
        handles.drone_collection = sim.createCollection(0)
        sim.addItemToCollection(handles.drone_collection, sim.handle_tree, handles.drone_root, 0)
        handles.collision_entity = requireObject(CONFIG.collision_entity_path, 'collision_entity_path')
    else
        handles.drone_collection = -1
        handles.collision_entity = -1
    end
end

function sysCall_init()
    resolveHandles()

    runtime.base_state_position = sim.getObjectPosition(handles.state_object, sim.handle_world)
    runtime.base_state_orientation = sim.getObjectOrientation(handles.state_object, sim.handle_world)
    runtime.base_control_position = sim.getObjectPosition(handles.control_object, sim.handle_world)
    runtime.base_goal_position = sim.getObjectPosition(handles.goal_object, sim.handle_world)
    runtime.final_goal_position = copyVector(runtime.base_goal_position)
    runtime.route_targets = {copyVector(runtime.base_goal_position)}
    runtime.active_route_index = 1
    runtime.pending_command = {0.0, 0.0, 0.0}
    runtime.collision_count = 0
    runtime.collision_active = false
    runtime.error_code = nil
    runtime.initialized = true
end

function sysCall_actuation()
    if not runtime.initialized then
        return
    end
    applyPendingCommand()
end

function sysCall_sensing()
    if not runtime.initialized then
        return
    end
    updateCollisionState()
end

function reset_episode(seed)
    if not runtime.initialized then
        error('EvalBridge not initialized')
    end

    runtime.episode_seed = seed
    runtime.pending_command = {0.0, 0.0, 0.0}
    runtime.collision_count = 0
    runtime.collision_active = false
    runtime.error_code = nil
    runtime.route_targets = {}
    runtime.active_route_index = 1

    math.randomseed(seed)

    local state_position = withJitter(runtime.base_state_position, CONFIG.start_position_jitter_m)
    runtime.final_goal_position = withJitter(runtime.base_goal_position, CONFIG.goal_position_jitter_m)
    runtime.route_targets = buildRouteTargets(state_position, runtime.final_goal_position)

    sim.setObjectPosition(handles.state_object, state_position, sim.handle_world)
    sim.setObjectOrientation(handles.state_object, runtime.base_state_orientation, sim.handle_world)
    sim.setObjectPosition(handles.control_object, runtime.base_control_position, sim.handle_world)
    moveVisibleGoalToActiveTarget()
    resetDynamicState()
end

function read_state()
    if not runtime.initialized then
        error('EvalBridge not initialized')
    end

    local position = sim.getObjectPosition(handles.state_object, sim.handle_world)
    updateRouteProgress(position)
    local velocity, angular_velocity = sim.getObjectVelocity(handles.state_object)
    if angular_velocity == nil then
        angular_velocity = {0.0, 0.0, 0.0}
    end
    local orientation = sim.getObjectOrientation(handles.state_object, sim.handle_world)
    local goal_position = getActiveRouteTarget()
    local final_goal_position = runtime.final_goal_position or goal_position
    local waypoint_distance = distance(position, goal_position)
    local success = runtime.active_route_index == #runtime.route_targets
        and waypoint_distance <= CONFIG.goal_tolerance_m

    return {
        position = copyVector(position),
        velocity = copyVector(velocity),
        goal_position = copyVector(goal_position),
        orientation = copyVector(orientation),
        angular_velocity = copyVector(angular_velocity),
        final_goal_position = copyVector(final_goal_position),
        final_goal_distance = distance(position, final_goal_position),
        waypoint_distance = waypoint_distance,
        route_mode = CONFIG.route_mode,
        route_phase = getRoutePhase(),
        active_route_index = runtime.active_route_index,
        route_target_count = #runtime.route_targets,
        route_turn_count = CONFIG.route_turn_count,
        route_turn_offset_m = CONFIG.route_turn_offset_m,
        is_final_route_target = runtime.active_route_index == #runtime.route_targets,
        pending_command = copyVector(runtime.pending_command),
        scaled_command = scaleVector(runtime.pending_command, CONFIG.speed_scale),
        speed_scale = CONFIG.speed_scale,
        max_linear_speed_mps = CONFIG.max_linear_speed_mps,
        goal_tolerance_m = CONFIG.goal_tolerance_m,
        route_waypoint_tolerance_m = CONFIG.route_waypoint_tolerance_m,
        simulation_timestep = sim.getSimulationTimeStep(),
        collision_count = runtime.collision_count,
        success = success,
        error_code = runtime.error_code,
        simulation_time = sim.getSimulationTime(),
    }
end

function apply_control(vx, vy, vz)
    if not runtime.initialized then
        error('EvalBridge not initialized')
    end

    runtime.pending_command = {
        clamp(vx, -CONFIG.max_linear_speed_mps, CONFIG.max_linear_speed_mps),
        clamp(vy, -CONFIG.max_linear_speed_mps, CONFIG.max_linear_speed_mps),
        clamp(vz, -CONFIG.max_linear_speed_mps, CONFIG.max_linear_speed_mps),
    }
end

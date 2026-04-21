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
-- Replace the object paths below so they match your scene. The default
-- command mode ("scene_specific") is a no-op until you wire the command into
-- your drone model's actuators. For quick smoke testing with a kinematic dummy,
-- you can switch command_mode to "kinematic_position".

local CONFIG = {
    drone_root_path = '/Drone',
    state_object_path = '/Drone',
    control_object_path = '/Drone',
    goal_object_path = '/Goal',
    collision_entity_path = nil,
    command_mode = 'scene_specific', -- 'scene_specific' or 'kinematic_position'
    reset_dynamic_root = false,
    goal_tolerance_m = 0.25,
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
}

local function copyVector(v)
    return {v[1], v[2], v[3]}
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
        current[1] + command[1] * dt,
        current[2] + command[2] * dt,
        current[3] + command[3] * dt,
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

    math.randomseed(seed)

    local state_position = withJitter(runtime.base_state_position, CONFIG.start_position_jitter_m)
    local goal_position = withJitter(runtime.base_goal_position, CONFIG.goal_position_jitter_m)

    sim.setObjectPosition(handles.state_object, state_position, sim.handle_world)
    sim.setObjectOrientation(handles.state_object, runtime.base_state_orientation, sim.handle_world)
    sim.setObjectPosition(handles.control_object, runtime.base_control_position, sim.handle_world)
    sim.setObjectPosition(handles.goal_object, goal_position, sim.handle_world)
    resetDynamicState()
end

function read_state()
    if not runtime.initialized then
        error('EvalBridge not initialized')
    end

    local position = sim.getObjectPosition(handles.state_object, sim.handle_world)
    local velocity = sim.getObjectVelocity(handles.state_object)
    local goal_position = sim.getObjectPosition(handles.goal_object, sim.handle_world)
    local success = distance(position, goal_position) <= CONFIG.goal_tolerance_m

    return {
        position = copyVector(position),
        velocity = copyVector(velocity),
        goal_position = copyVector(goal_position),
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

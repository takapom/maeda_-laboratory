package main

import (
	"fmt"
	"time"

	"gobot.io/x/gobot"
	"gobot.io/x/gobot/platforms/dji/tello"
)

func main() {
	drone := tello.NewDriver("8890") // Tello listens on UDP 8890

	work := func() {
		fmt.Println("Take off")
		drone.TakeOff()
		time.Sleep(4 * time.Second)

		fmt.Println("→ Move right a little")
		_ = drone.Right(20) // about 20 cm
		time.Sleep(2 * time.Second)

		fmt.Println("← Move left a little")
		_ = drone.Left(20) // return to near start
		time.Sleep(2 * time.Second)

		fmt.Println("Land")
		drone.Land()
		time.Sleep(3 * time.Second)
	}

	robot := gobot.NewRobot("tello",
		[]gobot.Connection{},
		[]gobot.Device{drone},
		work,
	)

	if err := robot.Start(); err != nil {
		panic(err)
	}
}

//左に動いて
//右に動いてドローンが一周まわるようなコードを生成して

package main

import (
	"fmt"
	"time"

	"gobot.io/x/gobot"
	"gobot.io/x/gobot/platforms/dji/tello"
)

func main() {
	// Tello listens on UDP 8890 by default.
	drone := tello.NewDriver("8890")

	work := func() {
		fmt.Println("Take off")
		drone.TakeOff()
		time.Sleep(4 * time.Second)

		fmt.Println("← Move left")
		_ = drone.Left(40) // ~40 cm left
		time.Sleep(2 * time.Second)

		fmt.Println("→ Move right")
		_ = drone.Right(40) // back toward start
		time.Sleep(2 * time.Second)

		fmt.Println("Rotate 360° clockwise")
		_ = drone.Clockwise(360)
		time.Sleep(4 * time.Second)

		fmt.Println("Land")
		drone.Land()
		time.Sleep(3 * time.Second)
	}

	robot := gobot.NewRobot("tello-left-right-spin",
		[]gobot.Connection{},
		[]gobot.Device{drone},
		work,
	)

	if err := robot.Start(); err != nil {
		panic(err)
	}
}

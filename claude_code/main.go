////右に少しだけ移動して左に少しだけ移動するコードを生成して

package main

import (
	"fmt"
	"time"

	"gobot.io/x/gobot"
	"gobot.io/x/gobot/platforms/dji/tello"
)

func main() {
	drone := tello.NewDriver("8890") // TelloはUDP 8890ポート

	work := func() {
		drone.TakeOff()

		fmt.Println("Take off!")
		time.Sleep(5 * time.Second)

		fmt.Println("Moving right...")
		drone.Right(20)
		time.Sleep(2 * time.Second)

		fmt.Println("Moving left...")
		drone.Left(20)
		time.Sleep(2 * time.Second)

		drone.Land()
		fmt.Println("Land!")
	}

	robot := gobot.NewRobot("tello",
		[]gobot.Connection{},
		[]gobot.Device{drone},
		work,
	)

	robot.Start()
}

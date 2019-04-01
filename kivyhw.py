# KivyHw demo project
# This is a small demonstration of using Kivy on a single-board computer
# to interact with an external microcontroller on a serial port connection.
#
# Edit the line below to select your USB serial port device
USBPORT = "/dev/ttyACM0"

import threading
from queue import Queue

from kivy import Config
from kivy.logger import Logger

from kivy.app import App
from kivy.properties import NumericProperty, BoundedNumericProperty
from kivy.uix.gridlayout import GridLayout
from kivy.clock import Clock, mainthread

from serial import Serial, SerialException, time

Config.set('kivy', 'log_level', 'info')
Config.set('graphics', 'fullscreen', 'auto')
Config.write()


class ArduinoDemo(GridLayout):
    """ This class represents the top-level Kivy window widget. """

    # Kivy uses Property objects to represent values like this
    # We use a mix of normal numeric and bounded numeric properties
    # Python code can read/write these properties, and the GUI will
    # automatically read/write these properties too (linking in .kv file)
    temp = NumericProperty(0)
    pot = BoundedNumericProperty(0, min=0, max=1023)
    humidity = NumericProperty(0)
    hue = BoundedNumericProperty(0, min=0, max=255)

    def __init__(self):
        super(ArduinoDemo, self).__init__()
        self.output_clock = None
        self.last_output = None

    # This function binds to the `hue` property defined above, and is called
    # whenever the hue property changes (when the user drags the slider).
    def on_hue(self, instance, value):
        """Called when the hue property changes"""
        Logger.debug("On_hue: {} ".format(value))

        # If we only want to output when people let go of the slider, we could send the output
        # from the `on_press_up` event handler, but since we want a relatively realtime
        # interaction, we use the `on_hue` handler.

        # To avoid spamming the microcontroller with constant updates while dragging the slider,
        # we use Kivy's Clock module to schedule the actual serial transmission a little bit
        # in the future, once the hue has stopped changing. We only schedule a call if there
        # isn't already a call scheduled (this gives us periodic updates while the slider is
        # being dragged around, plus one after the dragging stops).
        if not self.output_clock:
            self.output_clock = Clock.schedule_once(self.hue_stopped_changing, 0.05)

    # This function is schedule to run a little bit after each hue update
    def hue_stopped_changing(self, dt):
        output = chr(int(self.hue))
        Logger.debug("Sending hue value {} => {}".format(self.hue, output))
        self.output_clock = None
        App.get_running_app().queue.put(output)


class kivyhwApp(App):
    """ This class is the top-level Kivy application.
    It runs the Kivy main loop and also starts a separate thread just
    for serial port read/write. It uses a Queue to safely send new hue values
    to the serial port thread, and relies on the Kivy `@mainthread` function
    decorator to protect communicating the newly received temp/humidity/pot
    values from the serial port back to the main thread. The `stop_serial_thread`
    Event is used as a thread-safe communication medium so we can tell the
    serial thread to close the serial port and exit (otherwise the serial port
    can get locked-up if the thread dies without closing it first). """

    def build(self):
        self.queue = Queue()
        self.stop_serial_thread = threading.Event()
        self.serial_thread = None

        # We don't want to start processing serial before the app is ready,
        # so schedule the serial port thread creation a little bit in the future.
        Clock.schedule_once(self.start_serial_thread, 0.25)

        # Instantiate and return the root widget
        self.root = ArduinoDemo()
        return self.root

    def start_serial_thread(self, dt):
        """ Spin off a new thread to run `watch_serial()`, which manages the serial port read/write. """
        self.serial_thread = threading.Thread(target=self.watch_serial)
        self.serial_thread.start()

    def on_stop(self):
        """Called when the Kivy App wants to stop, so we can
        kill off our threads so they don't keep going."""
        self.stop_serial_thread.set()


    # Most GUI toolkits run the user interaction on a main thread, and
    # disallow updating the GUI widgets from any other thread.
    # This @mainthread function decorator uses some really cool Kivy magic
    # to ensure that it's safe to call this function from any thread (like
    # our serial port thread), and makes it safe and easy to update GUI
    # widgets from any thread.
    @mainthread
    def handle_serial_inputs(self, pot, temp, humidity):
        # Here we update the pre-defined Property objects with new values
        self.root.temp = temp
        self.root.humidity = humidity
        self.root.pot = pot

    def watch_serial(self):
        """This is what we run inside of the thread to watch for incoming serial."""
        # To make this a robust solution, we have two loops
        # Outer loop:
        #   Check if we need to stop the thread
        #   Otherwise, try to open the serial port and enter the inner loop
        # Inner loop:
        #   (serial port is already opened)
        #   Try to read and decode input values
        #   Check for and send any output value
        #   Check if we need to stop the thread
        while True:
            # Check if it's time to stop the thread
            if self.stop_serial_thread.is_set():
                return

            try:
                # We need a timeout so that we can check the stop thread event
                with Serial(USBPORT, 115200, timeout=0.05) as arduino:
                    while True:
                        reading = arduino.readline().decode()
                        if reading:
                            if reading.startswith(":") and reading.endswith("\n"):
                                try:
                                    reading = reading.strip(":$\r\n")
                                    pot, temp, humidity = reading.split(",")
                                    pot = int(pot)
                                    temp = int(temp)
                                    humidity = int(humidity)

                                    # This call to `handle_serial_inputs` is tricky.
                                    # It is not actually running this function in the serial port thread,
                                    # but rather some cool Kivy magic calls it on the main thread
                                    # (where it's safe to update GUI widgets).
                                    self.handle_serial_inputs(pot, temp, humidity)
                                except:
                                    # if we don't receive the whole message, it may not parse correctly
                                    pass

                        # Check if we have any hue update to send
                        if not self.queue.empty():
                            output = self.queue.get_nowait()
                            if output:
                                arduino.write(output.encode())

                        # Check if it's time to stop the thread
                        if self.stop_serial_thread.is_set():
                            return
            except SerialException:
                Logger.error("Error while opening or reading serial port.")
                time.sleep(5)


# Main program
if __name__ == '__main__':
    kivyhwApp().run()

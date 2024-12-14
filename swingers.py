
from machine import Pin, SPI
from hashlib import sha1
from ubinascii import hexlify
from urequests2 import get
from network import STA_IF, WLAN
import gc
from xpt2046 import Touch
from ili9341 import Display, color565
from xglcd_font import XglcdFont
#from touch_keyboard import TouchKeyboard
from time import sleep

spi1 = SPI(1, baudrate=51200000,sck=Pin(14), mosi=Pin(13), miso=Pin(12))
spi2 = SPI(2, baudrate=1000000,sck=Pin(25), mosi=Pin(32), miso=Pin(39))
bl_pin = Pin(21, Pin.OUT)  # Backlight pin setup (adjust pin as needed)
bl_pin.on()                # Power on the backlight   
  
  

class TouchKeyboard(object):
    """Touchscreen keyboard for ILI9341."""
    YELLOW = const(65504)
    GREEN = const(2016)

    KEYS = (
        (
            ('q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'),
            ('a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'),
            ('\t', 'z', 'x', 'c', 'v', 'b', 'n', 'm', '\b', '\b'),
            ('\n', ' ', '\r')
        ),
        (
            ('Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P'),
            ('A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L'),
            ('\t', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', '\b', '\b'),
            ('\n', ' ', '\r')
        ),
        (
            ('1', '2', '3', '4', '5', '6', '7', '8', '9', '0'),
            ('@', '#', '$', '%', '^', '&', '*', '(', ')'),
            ('\f', '+', ',', '.', '-', '_', '!', '?', '\b', '\b'),
            ('\a', ' ', '\r')
        ),
        (
            ('1', '2', '3', '4', '5', '6', '7', '8', '9', '0'),
            ('<', '>', '|', '\\', '/', '{', '}', '[', ']'),
            ('\f', '=', '"', '\'', ';', ':', '`', '~', '\b', '\b'),
            ('\a', ' ', '\r')
        )
    )

    def __init__(self, display, font):
        """Initialize Keybaord.
        Args:
            display (Display class): LCD Display
            font (XglcdFont class): Font to display text above keyboard
        """
        self.display = display
        self.font = font
        self.kb_screen = 0
        self.kb_text = ''
#        self.load_keyboard()
        self.waiting = False
        self.locked = False
        self.screen="splash"  
        self.load_splashscreen()
#        sleep (20)
#        self.load_keyboard()

    def clear_text(self):
        """Clear the keyboard text."""
        self.display.fill_hrect(0, 11, self.display.width, 24, 0)
        self.kb_text = ''

    def handle_keypress(self, x, y, debug=True):
        """Get  pressed key.
        Args:
            x, y (int): Pressed screen coordinates.
        Returns:
            bool: True indicates return pressed otherwise False
        """
        if self.locked is True:
            return

        if self.waiting is True:
            self.clear_text()
            self.waiting = False
            return

        x, y = y, x  # Touch coordinates need to be swapped.

        if debug:
            self.display.fill_circle(x, y, 5, self.GREEN)

###############################################################
        if ( self.screen == "splash" ):
            print ("in splash screen ")
            self.screen="keyboard"
            self.load_keyboard()
            return False

###############################################################
        # Calculate keyboard row and column
        if ( self.screen == "keyboard" ):
            if y >= 47:  # Check if press within keyboard area
                row = int(y / 47) - 1
                if row == 0:
                    column = int(x/32)
                elif row == 1 or row == 2:
                    column = max(0, int((x-16)/32))
                else:
                    # Row 3
                    if x < 80:
                        column = 0
                    elif x > 240:
                        column = 2
                    else:
                        column = 1

                key = self.KEYS[self.kb_screen][row][column]

                if key == '\t' or key == '\f':
                    self.kb_screen ^= 1           # Toggle caps or flip symbol sets
                    self.load_keyboard()
                elif key == '\a':
                    self.kb_screen = 0            # Switch to alphabet screen
                    self.load_keyboard()
                elif key == '\n':
                    self.kb_screen = 2            # Switch to numeric / symbols screen
                    self.load_keyboard()
                elif key == '\b':                 # Backspace
                    self.kb_text = self.kb_text[:-1]
                    margin = self.font.measure_text(self.kb_text)
                    self.display.fill_vrect(margin, 11, 12, 24, 0)
                elif key == '\r':
                    if self.kb_text != '':        # Keyboard return pressed (start search)
                        return True
                else:
                    margin = self.font.measure_text(self.kb_text)
                    self.kb_text += key
                    self.display.draw_letter(margin, 11, key, self.font,self.YELLOW)
            return False
 
############################################### 
    def load_splashscreen(self):
        """Display the currently selected keyboard."""
        self.display.clear()
        self.display.draw_image('images/2player-2.raw'.format(self.kb_screen),0, 0, 320, 240)

############################################### 
    def load_keyboard(self):
        """Display the currently selected keyboard."""
        self.display.clear()
        self.display.draw_image('images/kb{0}.raw'.format(self.kb_screen),0, 47, 320, 192)
        #self.display.draw_image('images/2player-2.raw'.format(self.kb_screen),0, 0, 320, 240)

############################################### 
    def show_message(self, msg, color):
        """Display message above keyboard."""
        self.clear_text()
        msg_length = self.font.measure_text(msg)
        margin = (self.display.width - msg_length) // 2
        self.display.draw_text(margin, 11, msg, self.font, color)
###############################################
        
  
class hooka(object):
    """Checks if password is pwned."""
    def __init__(self, spi1, spi2, dc=4, cs1=16, rst=17, cs2=5, rotation=270):
        
        # Set up display
        self.display = Display(spi1, dc=Pin(2), cs=Pin(15), rst=Pin(0), width=320, height=240, rotation=rotation)

        # Load font
        self.unispace = XglcdFont('fonts/Unispace12x24.c', 12, 24)

        # Set up Keyboard
        self.keyboard = TouchKeyboard(self.display, self.unispace)

        # Set up touchscreen
        self.xpt = Touch(spi2, cs=Pin(33), int_pin=Pin(36),int_handler=self.touchscreen_press)
        self.wlan = WLAN(STA_IF)

    def lookup(self, pwd):
        """Return the number of times password found in pwned database.
        Args:
            pwd: password to check
        Returns:
            integer: password hits from online pwned database.
        Raises:
            IOError: if there was an error due to WiFi network.
            RuntimeError: if there was an error trying to fetch data from dB.
            UnicodeError: if there was an error UTF_encoding the password.
        """
        sha1pwd = sha1(pwd.encode('utf-8')).digest()
        sha1pwd = hexlify(sha1pwd).upper().decode('utf-8')
        head, tail = sha1pwd[:5], sha1pwd[5:]

        if not self.wlan.isconnected():
            raise IOError('WiFi network error')

        hits = 0
        gc.collect()
        with get('https://api.pwnedpasswords.com/range/' + head) as response:
            for line in response.iter_lines():
                l = line.decode(response.encoding).split(":")
                if l[0] == tail:
                    hits = int(l[1])
                    break
        gc.collect()

        return hits

    def touchscreen_press(self, x, y):
        """Process touchscreen press events."""
        if self.keyboard.handle_keypress(x, y, debug=True) is True:  # this only happens when the keyboard enter key is pressed
            self.keyboard.locked = True                              # lock the keyboard and save the text .   
            pwd = self.keyboard.kb_text

            self.keyboard.show_message("Searching...", color565(0, 0, 255))
            try:
                hits = self.lookup(pwd)

                if hits:
                    # Password found
                    msg = "PASSWORD HITS: {0}".format(hits)
                    self.keyboard.show_message(msg, color565(255, 0, 0))
                else:
                    # Password not found
                    msg = "PASSWORD NOT FOUND"
                    self.keyboard.show_message(msg, color565(0, 255, 0))
            except Exception as e:
                if hasattr(e, 'message'):
                    self.keyboard.show_message(e.message[:22],color565(255, 255, 255))
                else:
                    self.keyboard.show_message(str(e)[:22],color565(255, 255, 255))

            self.keyboard.waiting = True
            self.keyboard.locked = False


def do_connect():
    import network
    sta_if = network.WLAN(network.WLAN.IF_STA)
    if not sta_if.isconnected():
        print('connecting to network...')
        sta_if.active(True)
        sta_if.connect('Ambrose-Fibre', 'mad1mad1')
        while not sta_if.isconnected():
            pass
    print('network config:', sta_if.ipconfig('addr4'))


def main():
    screen="splash"
    do_connect()
    hooka(spi1, spi2)

    while True:
        sleep(.1)


main()

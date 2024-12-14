
from machine import Pin, SPI, PWM, idle
from hashlib import sha1
#from ubinascii import hexlify
#from urequests2 import get
#from network import STA_IF, WLAN
#import gc
import time
import neopixel
import random
from xpt2046 import Touch
from ili9341 import Display, color565
from xglcd_font import XglcdFont
from time import sleep

# Constants
FLAG_LIMIT = 4  # Number of steps to reach the edge
NUM_POSITIONS = 2 * FLAG_LIMIT + 1  # Total flag positions (9 for -4 to +4)
LED_GROUP_SIZE = 3  # LEDs per flag position
NUM_LEDS = NUM_POSITIONS * LED_GROUP_SIZE  # Total LEDs (27 for 9 positions)
PRESS_DURATION_MS = 600  # Minimum press duration to score
DISABLE_TIME_MS = 1000  # Time to disable scoring after a point
MOVE_STEP = 1  # Movement per score
WIN_FLASH_DURATION = 5  # Duration to flash LEDs on win in seconds
CONSECUTIVE_HOOKS_LIMIT = 3  # Limit for consecutive hooks to win immediately

#GPIO Pins for switches and LED strip
spi1 = SPI(1, baudrate=51200000,sck=Pin(14), mosi=Pin(13), miso=Pin(12))
spi2 = SPI(2, baudrate=1000000,sck=Pin(25), mosi=Pin(32), miso=Pin(39))
bl_pin = Pin(21, Pin.OUT)  # Backlight pin setup (adjust pin as needed)
PLAYER1_PIN = 22
PLAYER2_PIN = 27
SPEAKER_PIN = 26
LED_PIN = 3  # This uses the rx pin  

# Hardware setup for switches and speaker
player1_switch = Pin(PLAYER1_PIN, Pin.IN, Pin.PULL_UP)
player2_switch = Pin(PLAYER2_PIN, Pin.IN, Pin.PULL_UP)
speaker = PWM(Pin(SPEAKER_PIN))
led_strip = neopixel.NeoPixel(Pin(LED_PIN, Pin.OUT), NUM_LEDS, timing=(350, 700, 800, 600))

# Flag and game state variables
flag_position = 0  # Start in the middle
player1_disabled_until = 0
player2_disabled_until = 0
player1_press_start = None
player2_press_start = None
player1_scored = False
player2_scored = False

# Power on the backlight and turn off the speaker 
bl_pin.on()               
Pin(LED_PIN).off()
speaker.duty_u16(0)

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
        #self.wlan = WLAN(STA_IF)


    def touchscreen_press(self, x, y):
        """Process touchscreen press events."""
        if self.keyboard.handle_keypress(x, y, debug=True) is True:
            # this only happens when the keyboard enter key is pressed
            self.keyboard.locked = True                              # lock the keyboard and save the text .   
            pwd = self.keyboard.kb_text
 
            self.keyboard.waiting = True
            self.keyboard.locked = False

def play_winning_tune():
    """Play a tune when a player wins."""
    melody = [440, 494, 523, 587, 659, 698, 784]  # A4, B4, C5, D5, E5, F5, G5
    for freq in melody:
        speaker.freq(freq)
        speaker.duty_u16(3000)  # Set duty cycle
        time.sleep(0.15)
    speaker.duty_u16(0)  # Turn off speaker


# Play sounds
def play_tune(player):
    """Play a short tune to indicate movement of the flag."""
    if player == 1:
        melody = [262, 330, 392]  # C4, E4, G4 for Player 1
    elif player == 2:
        melody = [392, 330, 262]  # G4, E4, C4 for Player 2
    for freq in melody:
        speaker.freq(freq)
        speaker.duty_u16(2000)  # Set duty cycle
        time.sleep(0.1)
    speaker.duty_u16(0)  # Turn off speaker

def flash_leds_randomly_for_winner(player):
    """Flash the winning player's side LEDs randomly."""
    end_time = time.time() + WIN_FLASH_DURATION
    while time.time() < end_time:
        for i in range(NUM_LEDS):
            if (player == 1 and i < NUM_LEDS // 2) or (player == 2 and i >= NUM_LEDS // 2):
                led_strip[i] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            else:
                led_strip[i] = (0, 0, 0)
        led_strip.write()
        time.sleep(0.1)

    # Clear LEDs after flashing
    for i in range(NUM_LEDS):
        led_strip[i] = (0, 0, 0)
    led_strip.write()

def display_flag():
    """Display the flag's position on the LED strip."""
    global flag_position

    # Clear all LEDs
    for i in range(NUM_LEDS):
        led_strip[i] = (0, 0, 0)

    # Calculate the group index for the current flag position
    group_index = flag_position + FLAG_LIMIT  # Map flag_position to group index
    group_start = group_index * LED_GROUP_SIZE
    group_end = min(group_start + LED_GROUP_SIZE, NUM_LEDS)  # Ensure we don't go out of bounds

    # Light up the LEDs in the current group
    for i in range(group_start, group_end):
        if flag_position == 0:
            led_strip[i] = (0, 255, 0)  # Green for center
        elif flag_position < 0:
            led_strip[i] = (255, 0, 0)  # Yellow for Player 1's side
        elif flag_position > 0:
            led_strip[i] = (0, 0, 255)  # Blue for Player 2's side

    # Write changes to the LED strip
    led_strip.write()

# Check if a player has won
def check_winner():
    """Check if the flag has moved past the limit."""
    global flag_position

    if flag_position == -FLAG_LIMIT - 1:
        print("Player 1 wins!")
        play_tune(1)
        flash_leds_randomly_for_winner(1)
        reset_game()
    elif flag_position == FLAG_LIMIT + 1:
        print("Player 2 wins!")
        play_tune(2)
        flash_leds_randomly_for_winner(2)
        reset_game()

def play_reset_tune():
    """Play a special tune if a hook is switched on during reset."""
    melody = [784, 698, 659, 587, 523, 494, 440]  # G5, F5, E5, D5, C5, B4, A4
    for freq in melody:
        speaker.freq(freq)
        speaker.duty_u16(3000)  # Set duty cycle
        time.sleep(0.1)
    speaker.duty_u16(0)  # Turn off speaker

def reset_game():
    """Reset the game state."""
    global flag_position, player1_consecutive_hooks, player2_consecutive_hooks

    # Ensure switches are released before starting the game
    print("Checking switches before starting...")
    while player1_switch.value() == 0 or player2_switch.value() == 0:
        if player1_switch.value() == 0:
            print("Player 1 switch is active!")
            flag_position = -4
            display_flag()
        if player2_switch.value() == 0:
            print("Player 2 switch is active!")
            flag_position = 4
            display_flag()
        play_reset_tune()  # Play warning tune
        time.sleep(0.5)  # Pause briefly before checking again

    print("All switches released. Game resetting...")
    flag_position = 0  # Reset flag position to center
    player1_consecutive_hooks = 0  # Reset Player 1's consecutive hooks
    player2_consecutive_hooks = 0  # Reset Player 2's consecutive hooks
    display_flag()  # Display the flag at the center

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
    speaker.duty_u16(0)
    screen="splash"
    hooka(spi1, spi2)      #Start screen and Touch 
    
    
    global flag_position
    global player1_disabled_until, player2_disabled_until
    global player1_press_start, player2_press_start
    global player1_scored, player2_scored
    global player1_consecutive_hooks, player2_consecutive_hooks

    print("Game starting... Tug-of-War begins!")
    reset_game()

    while True:
        current_time = time.ticks_ms()

        # Player 1: Handle button press
        if player1_switch.value() == 0:  # Button pressed
            if player1_press_start is None:
                player1_press_start = current_time
            elif not player1_scored and current_time >= player1_disabled_until:
                press_duration = time.ticks_diff(current_time, player1_press_start)
                if press_duration >= PRESS_DURATION_MS:
                    flag_position -= MOVE_STEP
                    player1_scored = True
                    player1_consecutive_hooks += 1
                    player2_consecutive_hooks = 0  # Reset Player 2's consecutive hooks
                    print(f"Player 1 moved the flag! Position: {flag_position}")
                    print(f"Player 1 consecutive hooks: {player1_consecutive_hooks}")
                    play_tune(1)
                    player1_disabled_until = current_time + DISABLE_TIME_MS
                    display_flag()
                    if player1_consecutive_hooks >= CONSECUTIVE_HOOKS_LIMIT:
                        print("Player 1 wins by consecutive hooks!")
                        play_winning_tune()
                        flash_leds_randomly_for_winner(1)
                        reset_game()
                    check_winner()
        else:  # Button released
            if player1_press_start is not None and time.ticks_diff(current_time, player1_press_start) < PRESS_DURATION_MS:
                print("Player 1 failed to press long enough. Consecutive hooks reset.")
                player1_consecutive_hooks = 0  # Reset consecutive hooks on miss
            player1_press_start = None
            player1_scored = False

        # Player 2: Handle button press
        if player2_switch.value() == 0:  # Button pressed
            if player2_press_start is None:
                player2_press_start = current_time
            elif not player2_scored and current_time >= player2_disabled_until:
                press_duration = time.ticks_diff(current_time, player2_press_start)
                if press_duration >= PRESS_DURATION_MS:
                    flag_position += MOVE_STEP
                    player2_scored = True
                    player2_consecutive_hooks += 1
                    player1_consecutive_hooks = 0  # Reset Player 1's consecutive hooks
                    print(f"Player 2 moved the flag! Position: {flag_position}")
                    print(f"Player 2 consecutive hooks: {player2_consecutive_hooks}")
                    play_tune(2)
                    player2_disabled_until = current_time + DISABLE_TIME_MS
                    display_flag()
                    if player2_consecutive_hooks >= CONSECUTIVE_HOOKS_LIMIT:
                        print("Player 2 wins by consecutive hooks!")
                        play_winning_tune()
                        flash_leds_randomly_for_winner(2)
                        reset_game()
                    check_winner()
        else:  # Button released
            if player2_press_start is not None and time.ticks_diff(current_time, player2_press_start) < PRESS_DURATION_MS:
                print("Player 2 failed to press long enough. Consecutive hooks reset.")
                player2_consecutive_hooks = 0  # Reset consecutive hooks on miss
            player2_press_start = None
            player2_scored = False

        time.sleep(0.01)  # Reduce CPU usage


main()

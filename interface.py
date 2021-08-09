import os
import pygame
import time
import random
from datetime import datetime

# adapted from "pyscope"


class Interface :
    screen = None;
    def __init__(self):
        pygame.display.init()

        size = (320, 240)
        self.screen = pygame.display.set_mode(size)
        self.screen.fill((0, 0, 0))        
        pygame.font.init()
        pygame.display.update()


    def __del__(self):
        "Destructor to make sure pygame shuts down, etc."

    def test(self):
        # Fill the screen with red (255, 0, 0)
        red = (255, 0, 0)
        self.screen.fill(red)
        # Update the display
        pygame.display.update()
        
        myfont = pygame.font.SysFont(pygame.font.get_default_font(), 24)
        textsurface = myfont.render('Jeremy', False, (0, 0, 0))
        self.screen.blit(textsurface, (0,0))


    def display_letters(self, text, size=24, bg=(0, 0, 0), fg=(0,0,0)):
        self.screen.fill(bg)
        # https://stackoverflow.com/questions/20842801/how-to-display-text-in-pygame
        myfont = pygame.font.SysFont(pygame.font.get_default_font(), size)
        textsurface = myfont.render(text, False, fg)
        self.screen.blit(textsurface, (0,0))
        pygame.display.update()

    def render_text(self, text, position=(0,0), size=32, font=None, fg=(255,255,255)):
        myfont = pygame.font.SysFont(font or pygame.font.get_default_font(), size)
        textsurface = myfont.render(text, False, fg)
        self.screen.blit(textsurface, position)

    BUFFER_X = 16
    BUFFER_Y = 16
    def render_main(self, pm2_5, pm10):
        background_color = (64, 70, 112)
        self.screen.fill(background_color)

        now = datetime.now().strftime("%a %-m/%d %-I:%M %p")
        self.render_text(now, position=(self.BUFFER_X, self.BUFFER_Y), size=48, font='DroidSansFallbackFull.ttf')
        aqi2_5 = f"{pm2_5: >3}" 
        print(aqi2_5)
        self.render_text(aqi2_5, position=(self.BUFFER_X, self.BUFFER_Y  * 2 + 48 ) , size=96, font='DroidSansFallbackFull.ttf')
        self.render_text("pm10", position=(self.BUFFER_X + 150, self.BUFFER_Y  * 2 + 48 ) , size=48, font='DroidSansFallbackFull.ttf')

        aqi10 = f"{pm10: >3}"
        print(aqi10)
        self.render_text(aqi10, position=(self.BUFFER_X, self.BUFFER_Y * 3 + 48 * 2 ) , size=96, font='DroidSansFallbackFull.ttf')
        self.render_text("pm2.5", position=(self.BUFFER_X + 150, self.BUFFER_Y * 3 + 48 * 2 ) , size=48, font='DroidSansFallbackFull.ttf')
        pygame.display.update()

    loading_status = 0
    def render_loading(self, timestep=0):
        background_color = (64, 70, 112)
        foreground_color = (200, 200, 200)
        highlight_color  = (255, 255, 255)
        faded_highlight_color = (220, 220, 220)
        self.screen.fill(background_color)

        time_font_size = 48
        now = datetime.now().strftime("%a %-m/%d %-I:%M %p")
        self.render_text(now, position=(self.BUFFER_X, self.BUFFER_Y), size=time_font_size)
        # do a little loading animation, sleeping time/n_steps per step

        radius = 10
        width_of_box = 75
        circles_buffer_x = self.BUFFER_X
        circles_buffer_y = self.BUFFER_Y + time_font_size + 12
        # clockwise from 11:30
        pygame.draw.circle(self.screen, highlight_color if timestep % 6 == 0 else foreground_color, (circles_buffer_x + width_of_box/3 - radius/6 ,       circles_buffer_y + radius ), radius)
        pygame.draw.circle(self.screen, highlight_color if timestep % 6 == 1 else foreground_color, (circles_buffer_x + width_of_box/3*2 + radius/6,      circles_buffer_y + radius ), radius)
        pygame.draw.circle(self.screen, highlight_color if timestep % 6 == 2 else foreground_color, (circles_buffer_x + width_of_box - radius, circles_buffer_y + width_of_box / 2 ), radius)
        pygame.draw.circle(self.screen, highlight_color if timestep % 6 == 3 else foreground_color, (circles_buffer_x + width_of_box/3*2 + radius/6,      circles_buffer_y + (width_of_box - radius) ), radius)
        pygame.draw.circle(self.screen, highlight_color if timestep % 6 == 4 else foreground_color, (circles_buffer_x + width_of_box/3 - radius/6,        circles_buffer_y + (width_of_box - radius) ), radius)
        pygame.draw.circle(self.screen, highlight_color if timestep % 6 == 5 else foreground_color, (circles_buffer_x + radius,                circles_buffer_y + width_of_box / 2 ), radius)

        pygame.display.update()


class RpiInterface(Interface):

    def __init__(self):
        "Ininitializes a new pygame screen using the framebuffer"
        # Based on "Python GUI in Linux frame buffer"
        # http://www.karoltomala.com/blog/?p=679
        disp_no = os.getenv("DISPLAY")
        if disp_no:
            print("I'm running under X display = {0}".format(disp_no))
        
        # Check which frame buffer drivers are available
        # Start with fbcon since directfb hangs with composite output
        drivers = ['fbcon', 'directfb', 'svgalib']
        found = False
        for driver in drivers:
            # Make sure that SDL_VIDEODRIVER is set
            if not os.getenv('SDL_VIDEODRIVER'):
                os.putenv('SDL_VIDEODRIVER', driver)
                print("driver", driver)
            try:
                pygame.display.init()
            except pygame.error:
                print('Driver: {0} failed.'.format(driver))
                continue
            found = True
            break
    
        if not found:
            raise Exception('No suitable video driver found!')
        
        size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
        print("Framebuffer size: %d x %d" % (size[0], size[1]))
        self.screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
        self.screen.fill((0, 0, 0))        
        pygame.font.init()
        pygame.display.update()

# Create an instance of the PyScope class
if __name__ == "__main__":
    scope = RpiInterface()
    scope.render_main(5, 10)
    slept = 0
    while True:
        events = pygame.event.get()
        for event in events:
            print(event)
        time.sleep(1)
        slept += 1
        if slept > 15:
            break
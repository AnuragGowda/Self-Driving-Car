from typing import Tuple

import pygame as pg
from math import cos, sin, pi, sqrt

class Racecar(pg.sprite.Sprite):

    ACCELERATION = 0.03
    BREAKING_PWR = 0.1
    ROTATION_PWR = 2

    def __init__(self):
        pg.sprite.Sprite.__init__(self)
        self.default_image = pg.transform.rotate(pg.transform.scale(pg.image.load("Assets/car.png"), (15,27)), -90)
        self.image = self.default_image
        self.rect = self.image.get_rect(center=(7.5,13.5))
        self.angle = 0
        self.is_accelerating = False
        self.is_breaking = False
        self.speed = 0
        self.x, self.y = (450,650)
        self.mask = pg.mask.from_surface(self.image)

        # information
        self.left_distance = 20
        self.center_distance = 100
        self.right_distance = 20


    def draw(self, surface):
        surface.blit(self.image, (self.x, self.y))
        
    def handle_input(self):

        key = pg.key.get_pressed()

        # Accelerate 
        self.is_accelerating = key[pg.K_UP]
        self.is_breaking = key[pg.K_DOWN] or key[pg.K_SPACE]

        # Turning
        rotation = 0
        if key[pg.K_LEFT]:
            rotation = 1
        elif key[pg.K_RIGHT]:
            rotation = -1
        
        if self.speed > 0 and rotation:
            self.angle += Racecar.ROTATION_PWR*rotation
            self.image = pg.transform.rotate(self.default_image, self.angle)
            self.rect = self.image.get_rect(center = self.rect.center)
            self.mask = pg.mask.from_surface(self.image)
    
    def update(self):
        radians = self.angle * pi/180
        if self.is_accelerating:
            self.speed += Racecar.ACCELERATION
        if self.is_breaking:
            self.speed -= Racecar.BREAKING_PWR
        
        if self.speed > 0:
            self.speed -= Game.FRICTION_COEFICIENT
    
        if self.speed > 0:
            self.x += self.speed * cos(radians)
            self.y -= self.speed * sin(radians)
        else:
            self.speed = 0
    
    def calculate_line_endpoint_with_collision(self, angle, mask):
        radians = angle * pi / 180
        max_length = 1000 
        x, y = self.x + self.rect.width / 2, self.y + self.rect.height / 2

        while max_length > 0:
            x += cos(radians)
            y -= sin(radians)
            if not mask.overlap(self.mask, (int(x) - mask.get_rect().x, int(y) - mask.get_rect().y)):
                max_length -= 1
            else:
                break
        
        return (x, y)
    
    def update_distances(self, mask):

        points = []
        distances = []

        for angle in [-30, 0, 30]:
            point = self.calculate_line_endpoint_with_collision(self.angle+angle, mask)
            distances.append(sqrt( ((point[0]) - (self.x-self.rect.width/2))**2 + ((point[1])-(self.y-self.rect.height/2))**2)) 
            points.append(point)
        
        self.left_distance = distances[0]
        self.center_distance = distances[1]
        self.right_distance = distances[2]

        return points


class Game:

    FRICTION_COEFICIENT = 0.01

    def __init__(
        self,
        screen_size: Tuple[int, int] = (700, 700),
        caption: str = "",
        tick_speed: int = 60,
    ):
        pg.init()
        pg.display.set_caption(caption)

        self.screen_size = screen_size
        self.screen = pg.display.set_mode(self.screen_size)
        self.clock = pg.time.Clock()
        self.tick_speed = tick_speed
        self.bg = pg.transform.scale(pg.image.load("Assets/map.png"), (700,700))
        
        # load mask
        self.offroad =  pg.transform.scale(pg.image.load("Assets/collision_mask.png"), (700,700))
        self.offroad_rect = self.offroad.get_rect()
        self.mask = pg.mask.from_surface(self.offroad)

        self.finishline = pg.Rect(470,605,15,90)
        self.startline = pg.Rect(520,605,15,90)

        self.car = Racecar()
        self.skid_marks = []

        self.running = True
        self.laptime = pg.time.get_ticks()
        self.pauseLaptime = None
        self.lap1 = False
        self.surfs = []

        self.counting_seconds = 0
        self.counting_millisecond = 0

    def should_quit(self):
        for event in pg.event.get():
            if event.type == pg.QUIT:
                self.running = False

    def reset(self):
        self.car.x, self.car.y = (450,650)
        self.car.speed = 0 
        
        self.car.angle = 0
        self.car.image = pg.transform.rotate(self.car.default_image, self.car.angle)
        self.car.rect = self.car.image.get_rect(center = self.car.rect.center)
        self.car.mask = pg.mask.from_surface(self.car.image)

        self.laptime = pg.time.get_ticks()
        self.lap1 = False

    def reset_screen(self):
        self.screen.blit(self.bg, (0, 0))


    def crash(self):

        if self.mask.overlap(self.car.mask, (self.car.x - self.mask.get_rect().x, self.car.y - self.mask.get_rect().y)):
            self.reset()

    def display_text(self):
        font = pg.font.SysFont(None, 25)
        if not self.pauseLaptime:
            counting_time = pg.time.get_ticks() - self.laptime
            self.counting_seconds = str( int((counting_time%60000)/1000 ))
            self.counting_millisecond = str(counting_time%1000).zfill(3)
        counting_string = "LAPTIME: %s.%s" % (self.counting_seconds, self.counting_millisecond)
        counting_text = font.render(counting_string, 1, (255,255,255))
        counting_rect = counting_text.get_rect()
        self.screen.blit(counting_text, counting_rect)

        speed_text = font.render(f"SPEED: {self.car.speed*15:.2f}", 1, (255,255,255))
        speed_rect = speed_text.get_rect(topleft = (0, 20))
        self.screen.blit(speed_text, speed_rect)

    def update_car(self):

        # Start and puase timer 
        if self.startline.collidepoint((self.car.x, self.car.y)):
            self.lap1 = True
        if self.lap1 and self.finishline.collidepoint(self.car.x, self.car.y):
            self.pauseLaptime = True

        self.car.handle_input()
        if self.car.is_breaking:
            self.skid_marks.append((self.car.x, self.car.y))
        for pos in self.skid_marks:
            left, right = pos
            skid_left = pg.Rect(left+2, right, 3, 3)
            skid_right = pg.Rect(left-2, right, 3, 3)
            pg.draw.rect(self.screen, (105,105,105), skid_left)
            pg.draw.rect(self.screen, (105,105,105), skid_right)

        # Draw car lines
        lines = self.car.update_distances(self.mask)
        for (x, y) in lines:
            pg.draw.line(self.screen, (255, 0, 0), (self.car.x + self.car.rect.width / 2, self.car.y + self.car.rect.height / 2), (x, y), 2)

        self.car.update()
        car_box_rect = pg.Rect(self.car.x, self.car.y, self.car.rect.width+1, self.car.rect.height+1)
        pg.draw.rect(self.screen, (0, 255, 0), car_box_rect, 2)

        self.car.draw(self.screen)
    

    def update(self):
        
        self.should_quit()
        self.reset_screen()
        self.crash()
        self.update_car()
        self.display_text()

        pg.display.update()
        self.clock.tick(self.tick_speed)

    def run(self):
        while self.running:
            self.update()
        pg.quit()


if __name__ == "__main__":
    game = Game()
    game.run()
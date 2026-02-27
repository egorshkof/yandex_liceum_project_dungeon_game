import arcade
import arcade.gui
import time

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "Dungeon Platformer"

TILE_SCALING = 1.0
PLAYER_SCALING = 0.35
ENEMY_SCALING = 0.35

GRAVITY = 1.2
PLAYER_MOVEMENT_SPEED = 5
PLAYER_JUMP_SPEED = 15

LAYER_OPTIONS = {
    "walls": {"use_spatial_hash": True},
    "ladders": {"use_spatial_hash": True},
}

# ---------------- WEAPON ---------------- #

class Weapon:
    def __init__(self, owner, cooldown):
        self.owner = owner
        self.cooldown = cooldown
        self.last_attack_time = 0

    def can_attack(self):
        return time.time() - self.last_attack_time >= self.cooldown

    def attack(self):
        self.last_attack_time = time.time()


class MeleeWeapon(Weapon):
    """Меч: создаёт hitbox перед персонажем"""
    def __init__(self, owner, damage=10, range_x=40, range_y=20, cooldown=0.5):
        super().__init__(owner, cooldown)
        self.damage = damage
        self.range_x = range_x
        self.range_y = range_y

    def attack(self, targets):
        if not self.can_attack():
            return

        # Конвертируем в SpriteList, если передан обычный list
        if not isinstance(targets, arcade.SpriteList):
            targets = arcade.SpriteList(targets)

        # Hitbox
        if self.owner.change_x >= 0:  # вправо
            center_x = self.owner.center_x + self.range_x
        else:  # влево
            center_x = self.owner.center_x - self.range_x

        hitbox = arcade.SpriteSolidColor(self.range_x, self.range_y, arcade.color.RED)
        hitbox.center_x = center_x
        hitbox.center_y = self.owner.center_y

        hit_targets = arcade.check_for_collision_with_list(hitbox, targets)
        for t in hit_targets:
            if isinstance(t, Character):
                t.take_damage(self.damage)

        self.last_attack_time = time.time()


class RangedWeapon(Weapon):
    """Лук: создаёт стрелы"""
    def __init__(self, owner, damage=5, speed=8, cooldown=2.0):
        super().__init__(owner, cooldown)
        self.damage = damage
        self.speed = speed

    def attack(self, target):
        if not self.can_attack():
            return None

        arrow = Arrow(
            self.owner.center_x,
            self.owner.center_y,
            target.center_x,
            target.center_y
        )
        arrow.damage = self.damage

        self.last_attack_time = time.time()
        return arrow


# ---------------- CHARACTERS ---------------- #

class Character(arcade.Sprite):
    def __init__(self, image, scale, max_hp):
        super().__init__(image, scale)
        self.max_hp = max_hp
        self.hp = max_hp
        self.speed = 2
        self.physics_engine = None

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp <= 0:
            self.kill()

    def is_alive(self):
        return self.hp > 0


class Arrow(arcade.Sprite):
    def __init__(self, start_x, start_y, target_x, target_y):
        super().__init__("assets/arrow.png", 0.3)
        self.center_x = start_x
        self.center_y = start_y
        dx = target_x - start_x
        dy = target_y - start_y
        length = (dx ** 2 + dy ** 2) ** 0.5
        speed = 8
        self.change_x = speed * dx / length
        self.change_y = speed * dy / length

    def update(self, delta_time=1/60):
        self.center_x += self.change_x
        self.center_y += self.change_y


class Player(Character):
    def __init__(self):
        super().__init__("assets/player.png", PLAYER_SCALING, max_hp=100)
        self.change_x = 0
        self.change_y = 0
        self.melee_weapon = MeleeWeapon(self, damage=20)
        self.ranged_weapon = RangedWeapon(self, damage=10)

    def attack_melee(self, enemies):
        self.melee_weapon.attack(enemies)

    def attack_ranged(self, target):
        self.ranged_weapon.attack(target)


class Enemy(Character):
    def __init__(self, image, scale, max_hp, aggro_range=300):
        super().__init__(image, scale, max_hp)
        self.aggro_range = aggro_range
        self.change_x = 0
        self.change_y = 0

    def update(self, player: Player):
        if not self.is_alive():
            return
        distance = arcade.get_distance_between_sprites(self, player)
        if distance <= self.aggro_range:
            if player.center_x > self.center_x:
                self.change_x = self.speed
            else:
                self.change_x = -self.speed
        else:
            self.change_x = 0
        if self.physics_engine:
            self.physics_engine.update()


class MeleeEnemy(Enemy):
    def __init__(self):
        super().__init__("assets/enemy_sword.png", ENEMY_SCALING, max_hp=50, aggro_range=250)
        self.speed = 2
        self.weapon = MeleeWeapon(self, damage=10)

    def update(self, player: Player):
        distance = arcade.get_distance_between_sprites(self, player)
        if distance <= self.aggro_range:
            self.change_x = self.speed if player.center_x > self.center_x else -self.speed
            self.weapon.attack(arcade.SpriteList([player]))
        if self.physics_engine:
            self.physics_engine.update()


class ArcherEnemy(Enemy):
    def __init__(self):
        super().__init__("assets/enemy_bow.png", ENEMY_SCALING, max_hp=30, aggro_range=400)
        self.speed = 0
        self.weapon = RangedWeapon(self)
        self.weapon.projectiles = arcade.SpriteList()

    def update(self, player: Player):
        distance = arcade.get_distance_between_sprites(self, player)
        if distance <= self.aggro_range:
            arrow = self.weapon.attack(player)
            if arrow:
                self.scene["Projectiles"].append(arrow)

        self.weapon.projectiles.update()
        if self.physics_engine:
            self.physics_engine.update()


# ---------------- GAME VIEW ---------------- #

class GameView(arcade.View):
    def __init__(self):
        super().__init__()
        self.scene = None
        self.player = None
        self.physics_engine = None
        self.camera = None
        self.gui_camera = None
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False
        self.projectiles = arcade.SpriteList()
        self.max_hp = 100
        self.hp = 100
        self.enemies = arcade.SpriteList()

    def setup(self):
        self.hp = self.max_hp
        tile_map = arcade.load_tilemap("assets/level_1.tmx", scaling=TILE_SCALING, layer_options=LAYER_OPTIONS)
        self.scene = arcade.Scene.from_tilemap(tile_map)

        # Player
        self.player = Player()
        self.player.center_x = 128
        self.player.center_y = 256
        self.scene.add_sprite("Player", self.player)

        # Enemies
        enemy1 = MeleeEnemy()
        enemy1.center_x = 600
        enemy1.center_y = 256
        enemy2 = ArcherEnemy()
        enemy2.center_x = 900
        enemy2.center_y = 300
        enemy2.scene = self.scene

        self.enemies.append(enemy1)
        self.enemies.append(enemy2)
        self.scene.add_sprite_list("Enemies", sprite_list=self.enemies)
        self.scene.add_sprite_list("Projectiles", sprite_list=self.projectiles)

        # PhysicsEnginePlatformer для всех
        self.physics_engine = arcade.PhysicsEnginePlatformer(self.player, walls=self.scene["walls"],
                                                             gravity_constant=GRAVITY, ladders=self.scene["ladders"])

        for enemy in self.enemies:
            enemy.physics_engine = arcade.PhysicsEnginePlatformer(enemy, walls=self.scene["walls"],
                                                                  gravity_constant=GRAVITY, ladders=self.scene["ladders"])

        # Cameras
        self.camera = arcade.Camera2D()
        self.gui_camera = arcade.Camera2D()

    # Input
    def on_key_press(self, key, modifiers):
        if key == arcade.key.A:
            self.left_pressed = True
        elif key == arcade.key.D:
            self.right_pressed = True
        elif key == arcade.key.W:
            self.up_pressed = True
        elif key == arcade.key.S:
            self.down_pressed = True
        elif key == arcade.key.SPACE:
            if self.physics_engine.can_jump():
                self.player.change_y = PLAYER_JUMP_SPEED
        elif key == arcade.key.J:  # melee attack
            self.player.attack_melee(self.enemies)
        elif key == arcade.key.K:
            if len(self.enemies) > 0:
                arrow = self.player.ranged_weapon.attack(self.enemies[0])
                if arrow:
                    self.projectiles.append(arrow)


def on_key_release(self, key, modifiers):
        if key == arcade.key.A:
            self.left_pressed = False
        elif key == arcade.key.D:
            self.right_pressed = False
        elif key == arcade.key.W:
            self.up_pressed = False
        elif key == arcade.key.S:
            self.down_pressed = False

    # Update
    def on_update(self, delta_time):
        self.player.change_x = 0
        if self.left_pressed:
            self.player.change_x = -PLAYER_MOVEMENT_SPEED
        elif self.right_pressed:
            self.player.change_x = PLAYER_MOVEMENT_SPEED

        if self.physics_engine.is_on_ladder():
            self.player.change_y = 0
            if self.up_pressed:
                self.player.change_y = PLAYER_MOVEMENT_SPEED
            elif self.down_pressed:
                self.player.change_y = -PLAYER_MOVEMENT_SPEED

        self.physics_engine.update()
        self.player.update()

        for enemy in self.enemies:
            enemy.update(self.player)
            if isinstance(enemy, MeleeEnemy):
                if arcade.check_for_collision(self.player, enemy):
                    self.hp -= 1
                    if self.hp < 0:
                        self.hp = 0

        if self.hp <= 0:
            self.setup()

        self.center_camera()

    # Camera
    def center_camera(self):
        self.camera.position = self.player.position

    # Draw
    def on_draw(self):
        self.clear()
        with self.camera.activate():
            self.scene.draw()
            for enemy in self.enemies:
                if isinstance(enemy, ArcherEnemy):
                    enemy.weapon.projectiles.draw()
        with self.gui_camera.activate():
            bar_width = 300
            bar_height = 25
            left = 50
            bottom = SCREEN_HEIGHT - 50
            arcade.draw_lbwh_rectangle_filled(left, bottom, bar_width, bar_height, arcade.color.DARK_RED)
            health_width = bar_width * (self.hp / self.max_hp)
            arcade.draw_lbwh_rectangle_filled(left, bottom, health_width, bar_height, arcade.color.RED)
            arcade.draw_text(f"HP: {self.hp}/{self.max_hp}", left, bottom - 20, arcade.color.WHITE, 14)


# ---------------- MENU ---------------- #

class MenuView(arcade.View):
    def __init__(self):
        super().__init__()
        self.manager = arcade.gui.UIManager()

    def on_show_view(self):
        self.manager.enable()
        self.manager.clear()
        start_button = arcade.gui.UIFlatButton(text="Играть", width=200, height=50)

        @start_button.event("on_click")
        def on_click(event):
            game = GameView()
            game.setup()
            self.window.show_view(game)

        v_box = arcade.gui.UIBoxLayout()
        v_box.add(start_button)

        anchor = arcade.gui.UIAnchorLayout()
        anchor.add(child=v_box, anchor_x="center_x", anchor_y="center_y")
        self.manager.add(anchor)

    def on_draw(self):
        self.clear()
        self.manager.draw()


# ---------------- MAIN ---------------- #

def main():
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    window.show_view(MenuView())
    arcade.run()


if __name__ == "__main__":
    main()

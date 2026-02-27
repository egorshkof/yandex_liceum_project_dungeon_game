import arcade
import arcade.gui
import time

from entities import (
    SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE,
    TILE_SCALING, LAYER_OPTIONS,
    Player, MeleeEnemy, ArcherEnemy, Enemy,
    GRAVITY, PLAYER_MOVEMENT_SPEED, PLAYER_JUMP_SPEED
)


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
        self.enemies = arcade.SpriteList()
        self.hp_text = None

    def setup(self):
        tile_map = arcade.load_tilemap("assets/level_1.tmx", scaling=TILE_SCALING, layer_options=LAYER_OPTIONS)
        self.scene = arcade.Scene.from_tilemap(tile_map)

        if "Projectiles" not in self.scene:
            self.scene.add_sprite_list("Projectiles")

        self.player = Player()
        self.player.center_x = 128
        self.player.center_y = 256
        self.scene.add_sprite("Player", self.player)

        enemy1 = MeleeEnemy()
        enemy1.center_x = 600
        enemy1.center_y = 256

        enemy2 = ArcherEnemy()
        enemy2.center_x = 950
        enemy2.center_y = 300

        self.enemies.extend([enemy1, enemy2])
        self.scene.add_sprite_list("Enemies", sprite_list=self.enemies)

        ladders = self.scene["ladders"] if "ladders" in self.scene else None

        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.player,
            walls=self.scene["walls"],
            gravity_constant=GRAVITY,
            ladders=ladders
        )

        for enemy in self.enemies:
            enemy.physics_engine = arcade.PhysicsEnginePlatformer(
                enemy,
                walls=self.scene["walls"],
                gravity_constant=GRAVITY,
                ladders=ladders
            )

        self.camera = arcade.Camera2D()
        self.gui_camera = arcade.Camera2D()

        self.hp_text = arcade.Text(
            text=f"HP: {int(self.player.hp)}/{self.player.max_hp}",
            x=50,
            y=SCREEN_HEIGHT - 70,
            color=arcade.color.WHITE,
            font_size=15,
            width=300,
            align="left",
            anchor_x="left",
            anchor_y="top"
        )

    def center_camera(self):
        self.camera.position = self.player.position

    def on_update(self, delta_time):
        self.player.change_x = 0
        if self.left_pressed:
            self.player.change_x = -PLAYER_MOVEMENT_SPEED
        if self.right_pressed:
            self.player.change_x = PLAYER_MOVEMENT_SPEED

        if self.physics_engine.is_on_ladder():
            self.player.change_y = 0
            if self.up_pressed:
                self.player.change_y = PLAYER_MOVEMENT_SPEED
            elif self.down_pressed:
                self.player.change_y = -PLAYER_MOVEMENT_SPEED

        self.physics_engine.update()
        self.player.update(delta_time)

        walls = self.scene["walls"] if "walls" in self.scene else arcade.SpriteList()

        for enemy in self.enemies:
            if isinstance(enemy, ArcherEnemy):
                enemy.update(self.player, delta_time, self.scene)
            elif isinstance(enemy, MeleeEnemy):
                enemy.update(self.player, delta_time, walls)
            else:
                enemy.update(self.player, delta_time)

        projectiles = self.scene["Projectiles"]
        for proj in list(projectiles):
            hit = False
            if proj.shooter is self.player:
                hits = arcade.check_for_collision_with_list(proj, self.enemies)
                for enemy in hits:
                    if enemy.is_alive():
                        enemy.take_damage(proj.damage)
                        hit = True
                        break
            elif isinstance(proj.shooter, Enemy):
                if arcade.check_for_collision(proj, self.player) and self.player.is_alive():
                    self.player.take_damage(proj.damage)
                    hit = True
            if hit:
                proj.kill()

        for enemy in self.enemies:
            if (isinstance(enemy, MeleeEnemy) and
                    enemy.is_alive() and
                    arcade.check_for_collision(self.player, enemy) and
                    enemy.melee.can_attack() and
                    self.player.is_alive()):
                self.player.take_damage(enemy.melee.damage)
                enemy.melee.last_attack_time = time.time()

        if not self.player.is_alive():
            self.setup()
            return

        self.hp_text.text = f"HP: {int(self.player.hp)}/{self.player.max_hp}"
        self.center_camera()
        projectiles.update(delta_time)

    def on_draw(self):
        self.clear()

        with self.camera.activate():
            self.scene.draw()
            self.scene["Projectiles"].draw()

        with self.gui_camera.activate():
            bar_width = 300
            bar_height = 25
            left = 50
            bottom = SCREEN_HEIGHT - 50

            arcade.draw_lbwh_rectangle_filled(left, bottom, bar_width, bar_height, arcade.color.DARK_RED)
            health_width = max(0, bar_width * (self.player.hp / self.player.max_hp))
            arcade.draw_lbwh_rectangle_filled(left, bottom, health_width, bar_height, arcade.color.RED)

            self.hp_text.draw()

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
        elif key == arcade.key.J:
            self.player.melee.attack(self.enemies)
        elif key == arcade.key.K:
            tx = self.player.center_x + 400 * self.player.facing
            ty = self.player.center_y
            self.player.ranged.attack(tx, ty, self.scene)

    def on_key_release(self, key, modifiers):
        if key == arcade.key.A:
            self.left_pressed = False
        elif key == arcade.key.D:
            self.right_pressed = False
        elif key == arcade.key.W:
            self.up_pressed = False
        elif key == arcade.key.S:
            self.down_pressed = False


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


def main():
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    window.show_view(MenuView())
    arcade.run()


if __name__ == "__main__":
    main()
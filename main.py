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
        self.mouse_world_x = 0
        self.mouse_world_y = 0
        self.background_music = arcade.load_sound("assets/music/background_loop.mp3")  # или .ogg, .wav
        self.music_player = None

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

        if self.music_player is None or not self.music_player.playing:
            self.music_player = arcade.play_sound(self.background_music, volume=0.35, loop=True)

    def on_mouse_motion(self, x, y, dx, dy):
        world = self.camera.unproject((x, y))
        self.mouse_world_x, self.mouse_world_y = world[0], world[1]

    def on_mouse_press(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            self.player.start_charging()

    def on_mouse_release(self, x, y, button, modifiers):
        if button == arcade.MOUSE_BUTTON_LEFT:
            world = self.camera.unproject((x, y))
            self.player.release_shot(world[0], world[1], self.scene)

    def center_camera(self):
        self.camera.position = self.player.position

    def on_update(self, delta_time):
        self.music_player.play()

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
            proj.center_x += proj.change_x * delta_time * 60
            proj.center_y += proj.change_y * delta_time * 60
            proj.lifetime -= delta_time

            if proj.lifetime <= 0:
                proj.kill()
                continue

            if arcade.check_for_collision_with_list(proj, walls):
                proj.kill()
                continue

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

            # ===== Полоска заряда =====
            if self.player.is_charging:
                ratio = min(1.0, self.player.charge_time / self.player.max_charge_time)

                bar_width = 60 * ratio
                bar_height = 8

                left = self.player.center_x - 30
                bottom = self.player.top + 20

                arcade.draw_lbwh_rectangle_filled(left, bottom, bar_width, bar_height, arcade.color.YELLOW)

            self.scene["Projectiles"].draw()

            # ===== HP БАРЫ ВРАГОВ =====
            for enemy in self.enemies:
                if not enemy.is_alive():
                    continue

                bar_width = 40
                bar_height = 6
                left = enemy.center_x - bar_width / 2
                bottom = enemy.top + 10

                arcade.draw_lbwh_rectangle_filled(left, bottom, bar_width, bar_height, arcade.color.DARK_RED)
                health_ratio = enemy.hp / enemy.max_hp
                arcade.draw_lbwh_rectangle_filled(left, bottom, bar_width * health_ratio, bar_height, arcade.color.RED)

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
            self.player.attack_melee(self.enemies)
        elif key == arcade.key.L:
            tx = self.player.center_x + 400 * self.player.facing
            ty = self.player.center_y
            self.player.attack_ranged(tx, ty, self.scene)
        elif key == arcade.key.E:
            self.player.try_open_chest(self.scene)
        elif key == arcade.key.ESCAPE:
            pause_view = PauseView(self)
            self.window.show_view(pause_view)

    def on_key_release(self, key, modifiers):
        if key == arcade.key.A:
            self.left_pressed = False
        elif key == arcade.key.D:
            self.right_pressed = False
        elif key == arcade.key.W:
            self.up_pressed = False
        elif key == arcade.key.S:
            self.down_pressed = False

    def on_hide_view(self):
        if self.music_player:
            self.music_player.pause()


class PauseView(arcade.View):
    def __init__(self, game_view):
        super().__init__()
        self.game_view = game_view

        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        arcade.set_background_color(arcade.color.BLACK[:3] + (160,))

        vbox = arcade.gui.UIBoxLayout(space_between=30)

        title = arcade.gui.UILabel(
            text="ПАУЗА",
            text_color=arcade.color.WHITE,
            font_size=48,
            width=400,
            height=80,
        )
        vbox.add(title)

        resume_btn = arcade.gui.UIFlatButton(
            text="Продолжить",
            width=300,
            height=60,
            style=self.game_view.button_style if hasattr(self.game_view, 'button_style') else None,
        )
        resume_btn.on_click = self.on_resume
        vbox.add(resume_btn)

        menu_btn = arcade.gui.UIFlatButton(
            text="В главное меню",
            width=300,
            height=60,
            style=self.game_view.button_style if hasattr(self.game_view, 'button_style') else None,
        )
        menu_btn.on_click = self.on_main_menu
        vbox.add(menu_btn)

        quit_btn = arcade.gui.UIFlatButton(
            text="Выйти из игры",
            width=300,
            height=60,
            style=self.game_view.button_style if hasattr(self.game_view, 'button_style') else None,
        )
        quit_btn.on_click = self.on_quit
        vbox.add(quit_btn)

        anchor = arcade.gui.UIAnchorLayout()
        anchor.add(vbox, anchor_x="center_x", anchor_y="center_y")
        self.manager.add(anchor)

    def on_resume(self, event):
        self.window.show_view(self.game_view)

    def on_main_menu(self, event):
        menu = MenuView()
        self.window.show_view(menu)

    def on_quit(self, event):
        arcade.exit()

    def on_draw(self):
        self.game_view.on_draw()

        arcade.draw_lbwh_rectangle_filled(
            left=0,
            bottom=0,
            width=SCREEN_WIDTH,
            height=SCREEN_HEIGHT,
            color=(0, 0, 0, 140)
        )

        self.manager.draw()

    def on_key_press(self, key, modifiers):
        if key == arcade.key.ESCAPE:
            self.window.show_view(self.game_view)

    def on_show_view(self):
        self.manager.enable()

    def on_hide_view(self):
        self.manager.disable()


class MenuView(arcade.View):
    def __init__(self):
        super().__init__()
        self.manager = arcade.gui.UIManager()
        self.manager.enable()

        arcade.set_background_color(arcade.color.BLACK)

        self.volume = 80.0
        self.fullscreen = False

        self.button_style = {
            "normal": arcade.gui.UIFlatButton.UIStyle(
                font_size=24,
                font_name="Times New Roman",
                font_color=arcade.color.WHITE,
                bg=arcade.color.DIM_GRAY,
            ),
            "hover": arcade.gui.UIFlatButton.UIStyle(
                font_size=24,
                font_name="Times New Roman",
                font_color=arcade.color.WHITE,
                bg=arcade.color.SLATE_GRAY,
            ),
            "press": arcade.gui.UIFlatButton.UIStyle(
                font_size=24,
                font_name="Times New Roman",
                font_color=arcade.color.WHITE,
                bg=arcade.color.DARK_SLATE_GRAY,
            ),
        }

        self.show_main_menu()

    def show_main_menu(self):
        self.manager.clear()

        vbox = arcade.gui.UIBoxLayout(space_between=20)

        title = arcade.gui.UILabel(
            text="Dungeon Platformer",
            text_color=arcade.color.LIGHT_GOLDENROD_YELLOW,
            font_size=48,
            font_name="Times New Roman",
            width=600,
        )

        vbox.add(title)
        vbox.add(arcade.gui.UISpace(height=40))

        play_btn = arcade.gui.UIFlatButton(
            text="Играть",
            width=280,
            height=60,
            style=self.button_style,
        )
        play_btn.on_click = self.on_play
        vbox.add(play_btn)

        settings_btn = arcade.gui.UIFlatButton(
            text="Настройки",
            width=280,
            height=60,
            style=self.button_style,
        )
        settings_btn.on_click = self.on_settings
        vbox.add(settings_btn)

        exit_btn = arcade.gui.UIFlatButton(
            text="Выход",
            width=280,
            height=60,
            style=self.button_style,
        )
        exit_btn.on_click = self.on_exit
        vbox.add(exit_btn)

        anchor = arcade.gui.UIAnchorLayout()
        anchor.add(vbox, anchor_x="center_x", anchor_y="center_y")
        self.manager.add(anchor)

    def show_settings(self):
        self.manager.clear()

        vbox = arcade.gui.UIBoxLayout(space_between=15)

        title = arcade.gui.UILabel(
            text="Настройки",
            text_color=arcade.color.LIGHT_CYAN,
            font_size=38,
            width=500,
        )
        vbox.add(title)
        vbox.add(arcade.gui.UISpace(height=30))

        # Громкость
        vol_label = arcade.gui.UILabel(
            text=f"Громкость: {int(self.volume)}%",
            font_size=22,
            width=400,
        )
        vbox.add(vol_label)

        vol_slider = arcade.gui.UISlider(
            value=self.volume,
            min=0,
            max=100,
            width=400,
            height=30,
        )

        def update_volume(event):
            self.volume = vol_slider.value
            vol_label.text = f"Громкость: {int(self.volume)}%"

        vol_slider.on_change = update_volume
        vbox.add(vol_slider)
        vbox.add(arcade.gui.UISpace(height=25))

        # Полноэкранный режим (кнопка-переключатель)
        fs_btn = arcade.gui.UIFlatButton(
            text=f"Полноэкранный режим: {'ВКЛ' if self.fullscreen else 'ВЫКЛ'}",
            width=340,
            height=50,
            style=self.button_style,
        )

        def toggle_fullscreen(event):
            self.fullscreen = not self.fullscreen
            self.window.set_fullscreen(self.fullscreen)
            fs_btn.text = f"Полноэкранный режим: {'ВКЛ' if self.fullscreen else 'ВЫКЛ'}"

        fs_btn.on_click = toggle_fullscreen
        vbox.add(fs_btn)
        vbox.add(arcade.gui.UISpace(height=30))

        # Назад
        back_btn = arcade.gui.UIFlatButton(
            text="Назад",
            width=220,
            height=50,
            style=self.button_style,
        )
        back_btn.on_click = lambda e: self.show_main_menu()
        vbox.add(back_btn)

        anchor = arcade.gui.UIAnchorLayout()
        anchor.add(vbox, anchor_x="center_x", anchor_y="center_y")
        self.manager.add(anchor)

    def on_play(self, event):
        game_view = GameView()
        game_view.setup()
        self.window.show_view(game_view)

    def on_settings(self, event):
        self.show_settings()

    def on_exit(self, event):
        arcade.exit()

    def on_show_view(self):
        self.manager.enable()

    def on_hide_view(self):
        self.manager.disable()

    def on_draw(self):
        self.clear()
        self.manager.draw()


def main():
    window = arcade.Window(
        width=SCREEN_WIDTH,
        height=SCREEN_HEIGHT,
        title=SCREEN_TITLE,
        resizable=True,
        antialiasing=True
    )
    window.show_view(MenuView())
    arcade.run()


if __name__ == "__main__":
    main()

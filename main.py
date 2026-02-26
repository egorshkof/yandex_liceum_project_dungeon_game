import arcade
import arcade.gui

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
SCREEN_TITLE = "Dungeon Platformer"

TILE_SCALING = 1.0
PLAYER_SCALING = 0.35

GRAVITY = 1.2
PLAYER_MOVEMENT_SPEED = 4
PLAYER_JUMP_SPEED = 15

LAYER_OPTIONS = {
    "walls": {"use_spatial_hash": True},
    "ladders": {"use_spatial_hash": True},
}


# ---------------- PLAYER ---------------- #

class Player(arcade.Sprite):
    def __init__(self):
        super().__init__("assets/player.png", PLAYER_SCALING)


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

        self.max_hp = 100
        self.hp = 100

    def setup(self):

        self.hp = self.max_hp

        tile_map = arcade.load_tilemap(
            "assets/level_0.tmx",
            scaling=TILE_SCALING,
            layer_options=LAYER_OPTIONS
        )

        self.scene = arcade.Scene.from_tilemap(tile_map)

        # --- Player ---
        self.player = Player()
        self.player.center_x = 128
        self.player.center_y = 256
        self.scene.add_sprite("Player", self.player)

        # --- Enemy example ---
        enemy = arcade.Sprite("assets/player.png", PLAYER_SCALING)
        enemy.center_x = 600
        enemy.center_y = 256
        self.scene.add_sprite("Enemies", enemy)

        # --- Physics ---
        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.player,
            walls=self.scene["walls"],
            gravity_constant=GRAVITY,
            ladders=self.scene["ladders"]
        )

        # --- Cameras ---
        self.camera = arcade.Camera2D()
        self.gui_camera = arcade.Camera2D()

    # -------- INPUT -------- #

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

    def on_key_release(self, key, modifiers):

        if key == arcade.key.A:
            self.left_pressed = False
        elif key == arcade.key.D:
            self.right_pressed = False
        elif key == arcade.key.W:
            self.up_pressed = False
        elif key == arcade.key.S:
            self.down_pressed = False

    # -------- UPDATE -------- #

    def on_update(self, delta_time):

        self.player.change_x = 0

        if self.left_pressed:
            self.player.change_x = -PLAYER_MOVEMENT_SPEED
        elif self.right_pressed:
            self.player.change_x = PLAYER_MOVEMENT_SPEED

        # --- Ladder ---
        if self.physics_engine.is_on_ladder():
            self.player.change_y = 0

            if self.up_pressed:
                self.player.change_y = PLAYER_MOVEMENT_SPEED
            elif self.down_pressed:
                self.player.change_y = -PLAYER_MOVEMENT_SPEED

        self.physics_engine.update()

        # --- Damage from enemies ---
        if "Enemies" in self.scene:
            hit_list = arcade.check_for_collision_with_list(
                self.player,
                self.scene["Enemies"]
            )

            if hit_list:
                self.hp -= 1

        if self.hp <= 0:
            self.setup()

        self.center_camera()

    # -------- CAMERA -------- #

    def center_camera(self):
        self.camera.position = self.player.position

    # -------- DRAW -------- #

    def on_draw(self):
        self.clear()

        with self.camera.activate():
            self.scene.draw()

        with self.gui_camera.activate():
            bar_width = 300
            bar_height = 25
            left = 50
            bottom = SCREEN_HEIGHT - 50

            # фон
            arcade.draw_lbwh_rectangle_filled(
                left,
                bottom,
                bar_width,
                bar_height,
                arcade.color.DARK_RED
            )

            # текущее здоровье
            health_width = bar_width * (self.hp / self.max_hp)

            arcade.draw_lbwh_rectangle_filled(
                left,
                bottom,
                health_width,
                bar_height,
                arcade.color.RED
            )

            arcade.draw_text(
                f"HP: {self.hp}/{self.max_hp}",
                left,
                bottom - 20,
                arcade.color.WHITE,
                14
            )


# ---------------- MENU VIEW ---------------- #

class MenuView(arcade.View):

    def __init__(self):
        super().__init__()
        self.manager = arcade.gui.UIManager()

    def on_show_view(self):
        self.manager.enable()
        self.manager.clear()

        start_button = arcade.gui.UIFlatButton(
            text="Играть",
            width=200,
            height=50
        )

        @start_button.event("on_click")
        def on_click(event):
            game = GameView()
            game.setup()
            self.window.show_view(game)

        v_box = arcade.gui.UIBoxLayout()
        v_box.add(start_button)

        anchor = arcade.gui.UIAnchorLayout()
        anchor.add(
            child=v_box,
            anchor_x="center_x",
            anchor_y="center_y"
        )

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
    print()

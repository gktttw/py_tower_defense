"""  
    !!! NOTICE !!!
    Please install pygame at first
    This is the code to use pip to install pygame in window console mode:
    python3 -m pip install -U pygame --user

    tower.py added IceTower(class)
    advanced_view.py added a classmethod under TowerView class to draw ice tower
    enemy AbstractEnemy add a variable if_slowed to check if it is slowed and immune_slow 
    enemy change color once is slowed
    andvance eneny immune to ice tower

"""
import tkinter as tk
from tkinter import messagebox
from tkinter import simpledialog
from tkinter import ttk

import gc
import os
import math

from model import TowerGame
from range_ import AbstractRange, CircularRange, PlusRange, DonutRange
from tower import SimpleTower, MissileTower, AbstractTower, PulseTower, AbstractObstacle, IceTower
from typing import Union
from enemy import SimpleEnemy, AbstractEnemy, AdvanceEnemy
from utilities import Stepper, rectangles_intersect, get_delta_through_centre
from utilities import Countdown, euclidean_distance, rotate_toward, angle_between, polar_to_rectangular, \
    rectangles_intersect
from view import GameView, TowerView
from level import AbstractLevel
from high_score_manager import HighScoreManager

# task 7 sound effect
from soundhandler import SoundHandler

BACKGROUND_COLOUR = "#4a2f48"
HIGHLIGHTED = "#4b3b4a"

__author__ = "DeShin Li"
__copyright__ = "44925817"


class BigEnemy(AbstractEnemy):
    """Enemy that is immune to projectile & explosive damage """
    name = "Big Enemy"
    colour = '#0000ff'

    points = 10

    def __init__(self, grid_size=(.4, .4), grid_speed=4/60, health=150):
        super().__init__(grid_size, grid_speed, health)

    def damage(self, damage, type_):
        """Inflict damage on the enemy

        Parameters:
            damage (int): The amount of damage to inflict
            type_ (str): The type of damage to do i.e. projectile, explosive, energy
        """
        if type_ != "projectile" and type_ != "explosive":
            self.health -= damage
        if self.health < 0:
            self.health = 0

    def step(self, data):
        """Move the enemy forward a single time-step

        Parameters:
            grid (GridCoordinateTranslator): Grid the enemy is currently on
            path (Path): The path the enemy is following

        Returns:
            bool: True iff the new location of the enemy is within the grid
        """
        grid = data.grid
        path = data.path

        # Repeatedly move toward next cell centre as much as possible
        movement = self.grid_speed
        while movement > 0:
            cell_offset = grid.pixel_to_cell_offset(self.position)

            # Assuming cell_offset is along an axis!
            offset_length = abs(cell_offset[0] + cell_offset[1])

            if offset_length == 0:
                partial_movement = movement
            else:
                partial_movement = min(offset_length, movement)

            cell_position = grid.pixel_to_cell(self.position)
            delta = path.get_best_delta(cell_position)

            # Ensures enemy will move to the centre before moving toward delta
            dx, dy = get_delta_through_centre(cell_offset, delta)

            speed = partial_movement * self.cell_size
            self.move_by((speed * dx, speed * dy))
            self.position = tuple(int(i) for i in self.position)

            movement -= partial_movement

        intersects = rectangles_intersect(*self.get_bounding_box(), (0, 0), grid.pixels)
        return intersects or grid.pixel_to_cell(self.position) in path.deltas

class EnergyTower(AbstractTower):
    """A energy tower that deals energy damage"""
    name = 'Energy Tower'
    colour = '#FEC40A'

    range = CircularRange(2)
    cool_down_steps = 0

    base_cost = 50
    level_cost = 15

    rotation_threshold = (1 / 6) * math.pi

    def __init__(self, cell_size: int, grid_size=(.7, .7), rotation=math.pi * .25, base_damage=15, level: int = 1):
        super().__init__(cell_size, grid_size, rotation, base_damage, level)

    def step(self, data):
        """Rotates toward 'target' and attacks if possible"""
        self.cool_down.step()

        target = self.get_unit_in_range(data.enemies)

        if target is None:
            return

        angle = angle_between(self.position, target.position)
        partial_angle = rotate_toward(self.rotation, angle, self.rotation_threshold)
        self.rotation = partial_angle

        if partial_angle == angle:
            target.damage(self.get_damage(), 'energy')


# Could be moved to a separate file, perhaps levels/simple.py, and imported
class MyLevel(AbstractLevel):
    """A simple game level containing examples of how to generate a wave"""
    waves = 20

    def get_wave(self, wave):
        """Returns enemies in the 'wave_n'th wave

        Parameters:
            wave_n (int): The nth wave

        Return:
            list[tuple[int, AbstractEnemy]]: A list of (step, enemy) pairs in the
                                             wave, sorted by step in ascending order 
        """
        enemies = []

        if wave == 1:
            # A hardcoded singleton list of (step, enemy) pairs

            enemies = [(10, SimpleEnemy())]
        elif wave == 2:
            # A hardcoded list of multiple (step, enemy) pairs

            enemies = [(10, SimpleEnemy()), (15, SimpleEnemy()), (30, SimpleEnemy())]
        elif 3 <= wave < 10:
            # List of (step, enemy) pairs spread across an interval of time (steps)

            steps = int(40 * (wave ** .5))  # The number of steps to spread the enemies across
            count = wave * 2  # The number of enemies to spread across the (time) steps

            for step in self.generate_intervals(steps, count):
                enemies.append((step, SimpleEnemy()))

        elif wave == 10:
            # Generate sub waves
            sub_waves = [
                # (steps, number of enemies, enemy constructor, args, kwargs)
                (50, 10, SimpleEnemy, (), {}),  # 10 enemies over 50 steps
                (100, None, None, None, None),  # then nothing for 100 steps
                (50, 10, SimpleEnemy, (), {}),  # then another 10 enemies over 50 steps
                (50, 5, BigEnemy, (), {}) # enemies that only take energy damage
            ]

            enemies = self.generate_sub_waves(sub_waves)

        else:  # 11 <= wave <= 20
            # Now it's going to get hectic

            sub_waves = [
                (
                    int(13 * wave),  # total steps
                    int(25 * wave ** (wave / 50)),  # number of enemies
                    SimpleEnemy,  # enemy constructor
                    (),  # positional arguments to provide to enemy constructor
                    {},  # keyword arguments to provide to enemy constructor
                ),
                (50, 1, AdvanceEnemy, (), {}) # advance enemy
                # ...
            ]
            enemies = self.generate_sub_waves(sub_waves)

        return enemies

class StatusBar(tk.Frame):
    """A frame that shows status of the game"""

    def __init__(self, parent, *args, **kwargs):
        """ Construct the frame
            prarmeters:
                parent (tk.Frame): Frame to place the StatusBar into
                *args and **kwargs: highlightbackground and highlightthickness options for tk.Frame

        """
        super().__init__(parent, *args, **kwargs)
        self._lb_wave = tk.Label(self, text="Wave")
        self._lb_wave.pack(side=tk.TOP)

        self._lb_score = tk.Label(self, text="Score")
        self._lb_score.pack(side=tk.TOP)

        self._down_bar = tk.Frame(self)
        self._down_bar.pack(side=tk.TOP, fill=tk.X)

        coin_photo = tk.PhotoImage(file="images/coins.gif")
        heart_photo = tk.PhotoImage(file="images/heart.gif")
        self._lb_coins = tk.Label(self._down_bar, image=coin_photo, text="Gold",compound=tk.LEFT)
        self._lb_coins.image = coin_photo
        self._lb_coins.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=20)

        self._lb_lives = tk.Label(self._down_bar, image=heart_photo, text="Lives",compound=tk.LEFT)
        self._lb_lives.image = heart_photo
        self._lb_lives.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=20)

    def set_wave(self, wave):
        """ Update the wave label
            Parameter: 
                wave(int): the current wave
        """
        self._lb_wave.config(text=f"Wave: {wave}/20")

    def set_score(self, score):
        """ Update the score label
            Parameter: 
                score(int): the current score
        """
        self._lb_score.config(text=f"{score}")

    def set_coins(self, coins):
        """ Update the coin label and consider the plurals
            Parameter: 
                coins(int): the current coin
        """
        if coins <= 1:
            self._lb_coins.config(text=f"{coins} coin")
        else:
            self._lb_coins.config(text=f"{coins} coins")

    def set_lives(self, lives):
        """ Update the live label and consider the plurals
            Parameter: 
                lives(int): the current live
        """
        if lives <= 1:
            self._lb_lives.config(text=f"{lives} life")
        else:
            self._lb_lives.config(text=f"{lives} lives")

class ShopTowerView(tk.Frame):
    """ A frame or a single item in Shop frame that shows the appreance, name and price of the tower"""

    def __init__(self, master, tower, click_command):
        """ Construct the frame
            prarmeters:
                master (tk.Frame): Frame to place the ShopTowerView into
                tower (AbstractTower): The tower that is to be presented, wiil be drawn in a canvas
                click_command (Function): a function that exectues select_tower(tower_class)
                
        """
        super().__init__(master)

        self._click_command = click_command
        self._master = master
        self._tower = tower

        self._canvas = tk.Canvas(self, height=30, width=30, highlightthickness=0, relief='ridge')
        self._canvas.pack(side=tk.LEFT, expand=False)
        tower.position = (tower.cell_size // 2, tower.cell_size // 2)  # Position in centre
        tower.rotation = 3 * math.pi / 2  # Point up
        TowerView.draw(self._canvas, tower)

        self._tower_name = tk.Label(self, text=tower.__class__.__name__, bg=BACKGROUND_COLOUR, fg="white")
        self._tower_name.pack(side= tk.TOP, expand= True, fill=tk.X)

        self._tower_price = tk.Label(self, text= tower.base_cost, bg=BACKGROUND_COLOUR, fg="white")
        self._tower_price.pack(side= tk.TOP, expand= True, fill=tk.X)
        
        # bind the canvas and the labels to _myselect_tower method
        self._canvas.bind('<Button-1>', self.pass_select_tower)
        self._tower_name.bind('<Button-1>', self.pass_select_tower)
        self._tower_price.bind('<Button-1>', self.pass_select_tower)

    def pass_select_tower(self, event):
        """ Exectue the select_tower function that passed into this instance
            Parameter:
                event (tk.Event): Tkinter mouse event
        """
        self._click_command()
        

    def set_available(self, available:bool):
        """ Update the tag color by its availablity
            Parameter: 
                available(bool): whether is it affordable
        """
        if available:
            self._tower_price.config(fg="white")
            self._tower_name.config(fg="white")
        else:
            self._tower_price.config(fg="red")
            self._tower_name.config(fg="red")

    def set_activated(self):
        """ Change the backbround to HIGHLIGHTED when it's selected"""
        self.config(bg=HIGHLIGHTED)
        self._canvas.config(bg=HIGHLIGHTED)
        self._tower_name.config(bg=HIGHLIGHTED)
        self._tower_price.config(bg=HIGHLIGHTED)

    def set_deactivated(self):
        """ Change the backbround to BACKGROUND_COLOUR when it's not selected"""
        self.config(bg=BACKGROUND_COLOUR)
        self._canvas.config(bg=BACKGROUND_COLOUR)
        self._tower_name.config(bg=BACKGROUND_COLOUR)
        self._tower_price.config(bg=BACKGROUND_COLOUR)
        

class TowerGameApp(Stepper):
    """Top-level GUI application for a simple tower defence game"""

    # All private attributes for ease of reading
    _current_tower = None
    _paused = False
    _won = None

    _level = None
    _wave = None
    _score = None
    _coins = None
    _lives = None

    _master = None
    _game = None
    _view = None

    def __init__(self, master: tk.Tk, delay: int = 20):
        """Construct a tower defence game in a root window

        Parameters:
            master (tk.Tk): Window to place the game into
        """

        self._master = master
        self._master.title("tower")
        super().__init__(master, delay=delay)

        # window close
        master.protocol("WM_DELETE_WINDOW", self._exit)

        self._game = game = TowerGame()

        self.setup_menu()

        # Add SoundHandler 
        self._sound_handler = SoundHandler()

        # if there's no high_scores.json in the current directory, create one and write a empth curly bracket
        if not os.path.exists("high_scores.json"):
            with open('high_scores.json', 'w+') as json_file:
                json_file.write('{}')

        # Highscore object
        self._highscore = HighScoreManager()

        # create a game view and draw grid borders
        self._view = view = GameView(master, size=game.grid.cells,
                                     cell_size=game.grid.cell_size,
                                     bg='antique white')
        view.pack(side=tk.LEFT, expand=True)

        # The main control on the right side of the game canvas
        # that contains statusbar, shop and playcontrol
        self._control_panel = tk.Frame(master, highlightbackground='yellow',
                             highlightthickness=5, bg=BACKGROUND_COLOUR)
        self._control_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Task 1.3 (Status Bar): instantiate status bar
        self._statusbar = StatusBar(self._control_panel,highlightbackground='red',
                             highlightthickness=5)
        self._statusbar.pack(side=tk.TOP, fill=tk.X)

        # Shop frame
        self._shop = tk.Frame(self._control_panel, highlightbackground='green',
                             highlightthickness=5, bg=BACKGROUND_COLOUR)
        self._shop.pack(side= tk.TOP, fill=tk.BOTH, expand=True)

        # Create views for each tower & store to update if availability changes
        towers = [SimpleTower, MissileTower, EnergyTower, IceTower]
        
        self._tower_views = []
        for tower_class in towers:
            tower = tower_class(self._game.grid.cell_size // 2)

            self._shoptowerview = ShopTowerView(self._shop, tower
                                 ,click_command=lambda class_=tower_class: self.select_tower(class_))
            self._shoptowerview.pack(side=tk.TOP, fill=tk.X)
            self._tower_views.append((tower, self._shoptowerview))
            # Can use to check if tower is affordable when refreshing view

        # Task 1.5 (Play Controls): instantiate widgets here
        self._playcontrols = tk.Frame(self._control_panel,highlightbackground='#cc0066',
                             highlightthickness=5)
        self._playcontrols.pack(side = tk.TOP)
        self.btn_next_wave = tk.Button(self._playcontrols, text="Next Wave",
                                        command = self.next_wave)
        self.btn_next_wave.pack(side=tk.LEFT)
        self.btn_pause = tk.Button(self._playcontrols, text="Pause",
                                        command = self._toggle_paused)
        self.btn_pause.pack(side=tk.LEFT)

        # Scale widget for controlling the volume of the game sound and bind it to update_volume function
        self.scale = tk.Scale(self._control_panel, from_=0.0, to=1.0, resolution=0.2, label="volume", command=self.update_volume,
                                bg=BACKGROUND_COLOUR, highlightthickness=0, fg="white")
        self.scale.set(1)
        self.scale.pack(side=tk.RIGHT)

        # Upgrade frame for upgrade
        self._upgrade_frame = tk.Frame(self._control_panel)
        self._upgrade_label = tk.Label(self._upgrade_frame, text="")
        self._upgrade_label.pack(side=tk.TOP)

        self.damage_lv = tk.IntVar()
        self.cooldown_lv = tk.IntVar()
        self._damage_selection = tk.Checkbutton(self._upgrade_frame, text = "damage", variable = self.damage_lv,
                            onvalue = 1, offvalue = 0, command=self.cancle_cooldown)
        self._damage_selection.pack(side=tk.LEFT)
        self._cooldown_selection = tk.Checkbutton(self._upgrade_frame, text = "cooldown", variable = self.cooldown_lv,
                            onvalue = 1, offvalue = 0, command=self.cancle_damage)
        self._cooldown_selection.pack(side=tk.LEFT)

        self._upgrade_btn = tk.Button(self._upgrade_frame, text="upgrade", command=self.upgrade_tower)
        self._upgrade_btn.pack(side=tk.BOTTOM)
        
        # bind game 
        game.on("enemy_death", self._handle_death)
        game.on("enemy_escape", self._handle_escape)
        game.on("cleared", self._handle_wave_clear)

        # Task 1.2 (Tower Placement): bind mouse events to canvas here
        self._view.bind('<Motion>', self._move)
        self._view.bind('<Button-1>', self._left_click)
        self._view.bind('<Leave>', self._mouse_leave)
        self._view.bind('<Button-3>', self._right_click)

        # Level
        self._level = MyLevel()

        self.select_tower(SimpleTower)

        self.current_upgrade_tower = SimpleTower

        view.draw_borders(game.grid.get_border_coordinates())

        # Get ready for the game
        self._setup_game()

        # Remove the relevant lines while attempting the corresponding section
        # Hint: Comment them out to keep for reference

        # Task 1.2 (Tower Placement): remove these lines
        """
        towers = [
            ([(2, 2), (3, 0), (4, 1), (4, 2), (4, 3)], SimpleTower),
            ([(2, 5)], MissileTower)
        ]

        for positions, tower in towers:
            for position in positions:
                game.place(position, tower_type=tower)


        # Task 1.5 (Tower Placement): remove these lines
        game.queue_wave([], clear=True)
        self._wave = 4 - 1  # first (next) wave will be wave 4
        self.next_wave()

        # Task 1.5 (Play Controls): remove this line
        self.start()
        """

    def update_volume(self, event):
        """Update the sound volume according to the scale bar
            use gc to get all SoundHandler instance and execute the update_volume method
            Parameter:
                event (tk.Event): Tkinter mouse event
        """
        
        for obj in gc.get_objects():
            if isinstance(obj, SoundHandler):
                obj.update_volume(self.scale.get())

    def coin_sound(self):
        """Coin sound effect"""

        self._sound_handler.play_sound("coin")

    def build_sound(self):
        """Place tower sound effect"""

        self._sound_handler.play_sound("build")

    def damage_sound(self):
        """Lose health sound effect"""

        self._sound_handler.play_sound("damage")

    def wave_sound(self):
        """Next wave sound effect"""

        self._sound_handler.play_sound("wave")

    def wrong_sound(self):
        """Couldn't afford or illegal position sound effect"""

        self._sound_handler.play_sound("wrong")

    def affordable(self):
        """Compare each tower value in shoptoweview frames and the current
            coins and update the label to red if it's not affordable
            Compare coins and update options
        """

        for tower, towerview in self._tower_views:
            if tower.base_cost <= self._coins:
                towerview.set_available(True)
            else:
                towerview.set_available(False)

        if self._coins < self.current_upgrade_tower.level_cost:
            self._damage_selection.config(fg="red")
            self._cooldown_selection.config(fg="red")
            self._upgrade_btn.config(state=tk.DISABLED)
        else:
            self._damage_selection.config(fg="black")
            self._cooldown_selection.config(fg="black")
            self._upgrade_btn.config(state=tk.ACTIVE)

    def setup_menu(self):
        """Sets up the application menu"""

        # Task 1.4: construct file menu here
        # ...
        menubar = tk.Menu(self._master)
        self._master.config(menu=menubar)

        filemenu = tk.Menu(menubar, tearoff = 0)
        filemenu.add_command(label="New Game", command=self._new_game)
        filemenu.add_command(label="Die", command=self._die)
        filemenu.add_command(label="I Need Money", command=self._add_money)
        filemenu.add_command(label="HighScores", command=self._show_highscore)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command = self._exit)
        menubar.add_cascade(label="File", menu=filemenu)

    def _toggle_paused(self, paused=None):
        """Toggles or sets the paused state and the background music

        Parameters:
            paused (bool): Toggles/pauses/unpauses if None/True/False, respectively
        """

        if paused is None:
            paused = not self._paused
            

        # Task 1.5 (Play Controls): Reconfigure the pause button here
        # ...

        if paused:
            self.pause()
            self.btn_pause.config(text="Play")
            self._sound_handler.pause_bg_music()
        else:
            self.start()
            self.btn_pause.config(text="Pause")
            self._sound_handler.unpause_bg_music()

        self._paused = paused

    def _setup_game(self):
        """Sets up the game"""

        self._wave = 0
        self._score = 0
        self._coins = 50
        self._lives = 20

        self._won = False

        self.affordable()

        # Task 1.3 (Status Bar): Update status here
        self._statusbar.set_wave(self._wave)
        self._statusbar.set_score(self._score)
        self._statusbar.set_coins(self._coins)
        self._statusbar.set_lives(self._lives)

        # Task 1.5 (Play Controls): Re-enable the play controls here (if they were ever disabled)
        self.btn_pause.config(state="normal")
        self.btn_next_wave.config(state="normal")

        self._game.reset()

        self._toggle_paused(paused=False)

        self._sound_handler.play_bg_music()

    # Task 1.4 (File Menu): Complete menu item handlers here (including docstrings!)
    def _new_game(self):
        """start a new game redraw every thing"""

        self._setup_game()
        self.refresh_view(True)


    def _exit(self):
        """promtp a dialog to confirm that whether they want to quit the application"""

        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            self._master.destroy()
        else:
            pass

    def _show_highscore(self):
        """ HighScore popup window(ttk.Treeview widget packed inside) list every entry in the json file"""

        highscore_window = tk.Tk()
        lb_highscore = tk.Label(highscore_window, text="TOP 10 LIST")
        lb_highscore.pack(side=tk.TOP)

        tree = ttk.Treeview(highscore_window, columns=("Name","Score"))
        tree.column("#0", width=40)
        tree.heading('#0', text='Place')
        tree.pack(side=tk.TOP)
        tree.heading("Name", text="Name")
        tree.column("Name", width=100)
        tree.heading("Score", text="Score")
        tree.column("Score", width=50)

        # insert every entry in json file to treeview
        result = self._highscore.get_entries()
        i = 1
        for entry in result:
            tree.insert('', 'end', text=i, values=(entry.get('name'), entry.get('score')))
            i += 1
        
        highscore_window.mainloop()

    def _die(self):
        """Lose immediately"""
        self._handle_game_over(False)

    def _add_money(self):
        """Add 100 coinds"""
        self._coins += 100
        self._statusbar.set_coins(self._coins)
        self.affordable()

    def refresh_view(self, force=False):
        """Refreshes the game view
            redraw enemies, towers and obstacles
        """
        if self._step_number % 2 == 0 or force:
            self._view.draw_enemies(self._game.enemies)
        self._view.draw_towers(self._game.towers)
        self._view.draw_obstacles(self._game.obstacles)

    def _step(self):
        """
        Perform a step every interval

        Triggers a game step and updates the view

        Returns:
            (bool) True if the game is still running
        """
        self._game.step()
        self.refresh_view()

        return not self._won

    # Task 1.2 (Tower Placement): Complete event handlers here (including docstrings!)
    # Event handlers: _move, _mouse_leave, _left_click
    def _move(self, event):
        """
        Handles the mouse moving over the game view canvas

        Parameter:
            event (tk.Event): Tkinter mouse event
        """

        # move the shadow tower to mouse position
        position = event.x, event.y
        self._current_tower.position = position

        legal, grid_path = self._game.attempt_placement(position)

        # find the best path and covert positions to pixel positions
        path = [self._game.grid.cell_to_pixel_centre(position)
                for position in grid_path.get_shortest()]

        # Task 1.2 (Tower placement): Draw the tower preview here
        # ...
        self._view.draw_preview(self._current_tower, legal)
        self._view.draw_path(path)

    def _mouse_leave(self, event):
        """Delete items from the gaming canvas once mouse leaves the canvas

            Parameter:
                event (tk.Event): Tkinter mouse event
        """
        # Task 1.2 (Tower placement): Delete the preview
        # Hint: Relevant canvas items are tagged with: 'path', 'range', 'shadow'

        self._view.delete('path', 'range', 'shadow')

    def _left_click(self, event):
        """ Left click to buy towers and deduct money
            if there's already a tower there, it will show the upgrade frame for that tower

            Parameter:
                event (tk.Event): Tkinter mouse event
        """
        # retrieve position to place tower
        if self._current_tower is None:
            return

        position = event.x, event.y
        cell_position = self._game.grid.pixel_to_cell(position)

        # check the position and place tower or upgrade tower
        if cell_position not in self._game.towers:
            if self._current_tower.base_cost > self._coins:
                print("You don't have enough coins.")
                self.wrong_sound()
                return
            else:
                if self._game.place(cell_position, tower_type=self._current_tower.__class__):
                    # Task 1.2 (Tower Placement): Attempt to place the tower being previewed
                    self.build_sound()
                    self.refresh_view()
                    self._coins -= self._current_tower.base_cost
                    self._statusbar.set_coins(self._coins)
                    self.affordable()
                    if self._current_tower.base_cost > self._coins:
                        self._view.delete('path', 'range', 'shadow')
        else:
            self.show_upgrade_tower(cell_position)

        

    def _right_click(self, event):
        """ Right click to sell towers and add money back and update every label about coins

            Parameter:
            event (tk.Event): Tkinter mouse event
        """

        position = event.x, event.y
        cell_position = self._game.grid.pixel_to_cell(position)

        try:
            tower = self._game.remove(cell_position)
            self._coins += int(tower.get_value()*0.8)
            self._statusbar.set_coins(self._coins)
            self.coin_sound()
            self.affordable()
            self.refresh_view()
        except KeyError:
            print(f"No tower exists at {cell_position}")
            self.wrong_sound()

    def next_wave(self):
        """Sends the next wave of enemies against the player"""
        if self._wave == self._level.get_max_wave():
            return

        self._wave += 1

        # Task 1.3 (Status Bar): Update the current wave display here
        # ...
        self._statusbar.set_wave(self._wave)

        # Task 1.5 (Play Controls): Disable the add wave button here (if this is the last wave)
        if self._wave == 20:
            self.btn_next_wave.config(state="disabled")

        # Generate wave and enqueue
        wave = self._level.get_wave(self._wave)
        for step, enemy in wave:
            enemy.set_cell_size(self._game.grid.cell_size)

        self._game.queue_wave(wave)
        self.wave_sound()

    def select_tower(self, tower):
        """
        Set 'tower' as the current tower and highlight the currently selected shoptowerview frame

        Parameters:
            tower (AbstractTower): The new tower type
        """
        self._current_tower = tower(self._game.grid.cell_size)

        self._upgrade_frame.pack_forget()

        # Highlight the selected tower and unhighlight who's not for the shoptowerviews
        for tower_view in self._tower_views:
            if tower.__name__ == tower_view[0].__class__.__name__:
                tower_view[1].set_activated()
            else:
                tower_view[1].set_deactivated()

    def _handle_death(self, enemies):
        """
        Handles enemies dying

        Parameters:
            enemies (list<AbstractEnemy>): The enemies which died in a step
        """
        bonus = len(enemies) ** .5
        for enemy in enemies:
            self._coins += enemy.points
            self._score += int(enemy.points * bonus)

        # Task 1.3 (Status Bar): Update coins & score displays here
        # ...
        self._statusbar.set_coins(self._coins)
        self._statusbar.set_score(self._score)
        self.affordable()

    def _handle_escape(self, enemies):
        """
        Handles enemies escaping (not being killed before moving through the grid

        Parameters:
            enemies (list<AbstractEnemy>): The enemies which escaped in a step
        """
        self._lives -= len(enemies)
        if self._lives < 0:
            self._lives = 0

        # kill those escaped enemies otherwise they will be still alive
        for enemy in enemies:
            enemy.health = 0

        # Task 1.3 (Status Bar): Update lives display here
        # ...
        self._statusbar.set_lives(self._lives)
        self.damage_sound()

        # Handle game over
        if self._lives == 0:
            self._handle_game_over(won=False)

    def _handle_wave_clear(self):
        """Handles an entire wave being cleared (all enemies killed)"""

        if self._wave == self._level.get_max_wave():
            self._handle_game_over(won=True)

    def _handle_game_over(self, won=False):
        """Handles game over, prompt question when the score is greater
        than the last entry form the json file
        
        Parameter:
            won (bool): If True, signals the game was won (otherwise lost)
        """
        self._won = won
        self.stop()
        self._sound_handler.stop_bg_music()

        # update the jason file or just show dialog
        if self._highscore.does_score_qualify(self._score):
            result = simpledialog.askstring("HighScore!", "Enter you name")
            self._highscore.add_entry(result, self._score)
            self._highscore.save()
        else:
            if self._won:
                dialog = "You Won"
            else:
                dialog = "You Lose"
            # Task 1.4 (Dialogs): show game over dialog here
            messagebox.showinfo("Game Over", dialog)

        # Task 1.5 (Play Controls): disable both buttons when game is over
        self.btn_pause.config(state="disabled")
        self.btn_next_wave.config(state="disabled")

    def show_upgrade_tower(self, cell_position):
        """ show the selected tower config to the _upgrade_frame
            parameter:
                cell_position(tuple): the cell positon where the mouse clicked on canvas

            note that only simple tower and missile tower can be upgraded
            cool_down_step of missile tower is 10, so make sure it can't be negative value
        """

        self.current_upgrade_tower = self._game.towers[cell_position]

        # reset the upgrade frame
        self._upgrade_frame.pack_forget()
        self._upgrade_frame.pack(side=tk.LEFT)
        self.damage_lv.set(0)
        self.cooldown_lv.set(0)
        self._upgrade_label.config(text=f"{self._game.towers[cell_position].name} lv.{self._game.towers[cell_position].level}")
        self._damage_selection.config(text=f"damage ${self.current_upgrade_tower.level_cost}")
        self._cooldown_selection.config(text=f"cooldown ${self.current_upgrade_tower.level_cost}")

        # config upgrade solution for each tower
        if self._game.towers[cell_position].__class__.__name__ == "SimpleTower":
            # simple tower can't be cooled down anymore
            self._damage_selection.config(state=tk.ACTIVE)
            self._cooldown_selection.config(state=tk.DISABLED)
            self._upgrade_btn.config(state=tk.ACTIVE)
        elif self._game.towers[cell_position].__class__.__name__ == "MissileTower":
            # missile tower can be cooled down but if the cool down step reaches to 0 it will be disabled
            self._damage_selection.config(state=tk.ACTIVE)
            if self._game.towers[cell_position].cool_down_steps == 0:
                self._cooldown_selection.config(state=tk.DISABLED)
            else:
                self._cooldown_selection.config(state=tk.ACTIVE)
            self._upgrade_btn.config(state=tk.ACTIVE)
        else:
            # other tower are not upgradable
            self._damage_selection.config(state=tk.DISABLED)
            self._cooldown_selection.config(state=tk.DISABLED)
            self._upgrade_btn.config(state=tk.DISABLED)

    def upgrade_tower(self):
        """Alter the selected tower and change its value and update the label on upgrade frame too
            deduct money
        """

        if self.damage_lv.get() == 1:
            self.current_upgrade_tower.base_damage += 3
            self.current_upgrade_tower.level += 1
            self._upgrade_label.config(text=f"{self.current_upgrade_tower.name} lv.{self.current_upgrade_tower.level}")
            
        if self.cooldown_lv.get() == 1:
            self.current_upgrade_tower.cool_down_steps -= 1
            self.current_upgrade_tower.cool_down = Countdown(self.current_upgrade_tower.cool_down_steps)
            self.current_upgrade_tower.level += 1
            self._upgrade_label.config(text=f"{self.current_upgrade_tower.name} lv.{self.current_upgrade_tower.level}")

        self._coins -= self.current_upgrade_tower.level_cost
        self.affordable()
        self._upgrade_frame.pack_forget()

    def cancle_cooldown(self):
        """cancle the upgrade cooldown option because you can only pick one"""
        self.cooldown_lv.set(0)
        
    def cancle_damage(self):
        """cancle the upgrade damage option because you can only pick one"""
        self.damage_lv.set(0)


        
# Task 1.1 (App Class): Instantiate the GUI here
# ...

def main():
    root = tk.Tk()
    tower = TowerGameApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
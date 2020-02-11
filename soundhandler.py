"""  
    !!! NOTICE !!!
    Please install pygame at first
    This is the code to use pip to install pygame in window console mode:
    python3 -m pip install -U pygame --user

    The SoundHandler class is used in game to play sound effect
"""
import pygame

class SoundHandler(object):
    """ An object that handles sound effect"""
    def __init__(self):
        """ initial pygame mixer and import sound file"""
        pygame.mixer.init(44100)

        self.coin_sound = pygame.mixer.Sound("sound/coin.wav")
        # https://www.youtube.com/audiolibrary/soundeffects
        self.build_sound = pygame.mixer.Sound("sound/Metal_Hits.wav")
        # https://www.youtube.com/audiolibrary/soundeffects
        self.damage_sound = pygame.mixer.Sound("sound/Hit_with_Club.wav")
        # https://www.youtube.com/audiolibrary/soundeffects
        self.wave_sound = pygame.mixer.Sound("sound/Ship_Bell.wav")
        # https://www.youtube.com/audiolibrary/soundeffects
        self.missile_sound = pygame.mixer.Sound("sound/Swoosh.wav")
        # https://www.youtube.com/audiolibrary/soundeffects
        self.wrong_sound = pygame.mixer.Sound("sound/wrong_answer.wav")
        # http://www.orangefreesounds.com/

        pygame.mixer.music.load("sound/Arpanauts.mp3")
        # http://ericskiff.com/music/

        self.sound_dict = {'coin':self.coin_sound, 'build':self.build_sound, 'damage':self.damage_sound,
            'wave':self.wave_sound, 'wrong':self.wrong_sound, 'missile':self.missile_sound}

    def update_volume(self, volumn):
        """ update the sound volume according to the scale bar
            parameter:
                volumn(float): The value from the scale bar
        """
        for sound in self.sound_dict.values():
            sound.set_volume(volumn)
        pygame.mixer.music.set_volume(volumn)

    def play_sound(self, sound):
        """ play sound effect
            parameter:
                sound(str): The name of the sound that can be looked up in the self.sound_dict
        """
        self.sound_dict.get(sound).play()

    def play_bg_music(self):
        """play background music infinite loop"""
        pygame.mixer.music.play(-1)

    def pause_bg_music(self):
        """pause background music"""
        pygame.mixer.music.pause()

    def unpause_bg_music(self):
        """uppause background music"""
        pygame.mixer.music.unpause()

    def stop_bg_music(self):
        """end background music"""
        pygame.mixer.music.stop()

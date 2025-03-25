from django.db import models

class Card(models.Model):
    SUITS = [('♠', 'Spades'), ('♥', 'Hearts'), ('♦', 'Diamonds'), ('♣', 'Clubs')]
    RANKS = [('7', 7), ('8', 8), ('9', 9), ('10', 10), ('J', 10), ('Q', 10), ('K', 10), ('A', 11)]

    rank = models.CharField(max_length=2, choices=[(r[0], r[0]) for r in RANKS])
    suit = models.CharField(max_length=1, choices=SUITS)

    def __str__(self):
        return f"{self.rank}{self.suit}"

class Player(models.Model):
    name = models.CharField(max_length=50)
    chips = models.IntegerField(default=100)

    def __str__(self):
        return self.name

class Game(models.Model):
    STAGE_CHOICES = [
        ('pre_bet', 'Залагане на тъмно'),
        ('pre_bet_computer', 'Компютър залага на тъмно'),
        ('betting', 'Залагане'),
        ('showdown', 'Показване'),
        ('svara', 'Свара'),
    ]
    players = models.ManyToManyField(Player, through='PlayerHand')
    pot = models.IntegerField(default=0)
    dark_bet = models.IntegerField(default=0)
    svara_pot = models.IntegerField(default=0)
    dealer = models.ForeignKey(Player, on_delete=models.SET_NULL, null=True, related_name='dealt_games')
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES, default='pre_bet')

class PlayerHand(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    cards = models.ManyToManyField(Card)
    bet = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
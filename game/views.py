from django.shortcuts import render, redirect
from .models import Card, Player, Game, PlayerHand
from .utils import calculate_points
import random

def home(request):
    return render(request, 'game/home.html')

def start_game(request):
    if request.method == 'POST':
        num_players = int(request.POST.get('players', 2))

        Player.objects.all().delete()
        for i in range(num_players):
            Player.objects.create(name=f'Player {i + 1}')

        deck = list(Card.objects.all())
        if not deck:
            for rank, _ in Card.RANKS:
                for suit, _ in Card.SUITS:
                    Card.objects.create(rank=rank, suit=suit)
            deck = list(Card.objects.all())

        game = Game.objects.create(dealer=Player.objects.first())
        players = Player.objects.all()

        for player in players:
            hand = PlayerHand.objects.create(player=player, game=game)
            cards = random.sample(deck, 3)
            hand.cards.set(cards)
            for card in cards:
                deck.remove(card)

        return redirect('game_view', game_id=game.id)

    return redirect('home')

def game_view(request, game_id):
    game = Game.objects.get(id=game_id)
    hands = PlayerHand.objects.filter(game=game)

    scores = {hand.player.name: calculate_points(hand.cards.all()) for hand in hands}
    winner = max(scores, key=scores.get) if scores else None

    context = {
        'game': game,
        'hands': hands,
        'scores': scores,
        'winner': winner,
    }
    return render(request, 'game/game.html', context)
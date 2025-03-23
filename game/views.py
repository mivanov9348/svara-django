from django.shortcuts import render, redirect
from .models import Card, Player, Game, PlayerHand
from .utils import calculate_points
import random

def home(request):
    return render(request, 'game/home.html')

def start_game(request):
    if request.method == 'POST':
        num_players = int(request.POST.get('players', 2))

        # Изтриваме стари данни
        Player.objects.all().delete()
        for i in range(num_players):
            Player.objects.create(name=f'Player {i + 1}')

        # Създаваме тесте
        deck = list(Card.objects.all())
        if not deck:
            for rank, _ in Card.RANKS:
                for suit, _ in Card.SUITS:
                    Card.objects.create(rank=rank, suit=suit)
            deck = list(Card.objects.all())

        # Създаваме игра
        game = Game.objects.create(dealer=Player.objects.first(), stage='deal')
        players = Player.objects.all()

        # Раздаваме по 3 карти
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
    context = {'game': game, 'hands': hands}

    if game.stage == 'deal':
        if request.method == 'POST':
            game.stage = 'betting'
            game.save()
            return redirect('game_view', game_id=game.id)

    elif game.stage == 'betting':
        if request.method == 'POST':
            player_id = request.POST.get('player_id')
            action = request.POST.get('action')
            bet_amount = int(request.POST.get('bet', 0))

            hand = PlayerHand.objects.get(player_id=player_id, game=game)
            player = hand.player

            if action == 'fold':
                hand.is_active = False
            elif action == 'bet' and bet_amount <= player.chips:
                hand.bet += bet_amount
                player.chips -= bet_amount
                game.pot += bet_amount
                player.save()

            hand.save()

            active_hands = hands.filter(is_active=True)
            if all(h.bet > 0 or not h.is_active for h in hands) and active_hands.count() <= 1:
                game.stage = 'showdown'
                game.save()

            return redirect('game_view', game_id=game.id)

    elif game.stage == 'showdown':
        active_hands = hands.filter(is_active=True)
        scores = {hand.player.name: calculate_points(hand.cards.all()) for hand in active_hands}
        winner_name = max(scores, key=scores.get) if scores else None
        if winner_name:
            winner = Player.objects.get(name=winner_name)
            winner.chips += game.pot
            winner.save()
        context['scores'] = scores
        context['winner'] = winner_name

    return render(request, 'game/game.html', context)
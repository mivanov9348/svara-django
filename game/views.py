from django.shortcuts import render, redirect
from .models import Card, Player, Game, PlayerHand
from .utils import calculate_points
import random


def home(request):
    return render(request, 'game/home.html')


def start_game(request):
    if request.method == 'POST':
        Player.objects.all().delete()
        Game.objects.all().delete()
        PlayerHand.objects.all().delete()

        you = Player.objects.create(name='You', chips=100)
        computer = Player.objects.create(name='Computer', chips=100)
        entry_fee = 5

        deck = list(Card.objects.all())
        if not deck:
            for rank, _ in Card.RANKS:
                for suit, _ in Card.SUITS:
                    Card.objects.create(rank=rank, suit=suit)
            deck = list(Card.objects.all())

        game = Game.objects.create(dealer=you, stage='pre_bet', pot=entry_fee * 2)
        you.chips -= entry_fee
        computer.chips -= entry_fee
        you.save()
        computer.save()

        your_hand = PlayerHand.objects.create(player=you, game=game)
        computer_hand = PlayerHand.objects.create(player=computer, game=game)

        your_cards = random.sample(deck, 3)
        your_hand.cards.set(your_cards)
        for card in your_cards:
            deck.remove(card)

        computer_cards = random.sample(deck, 3)
        computer_hand.cards.set(computer_cards)

        return redirect('game_view', game_id=game.id)
    return redirect('home')


def game_view(request, game_id):
    game = Game.objects.get(id=game_id)
    your_hand = PlayerHand.objects.get(game=game, player__name='You')
    computer_hand = PlayerHand.objects.get(game=game, player__name='Computer')
    dark_bet = getattr(game, 'dark_bet', 0)
    min_bet = dark_bet * 2 if dark_bet > 0 else 0
    svara_entry_fee = game.svara_pot // 2 if hasattr(game, 'svara_pot') else 0

    # Изчисляване на точките
    your_score = calculate_points(your_hand.cards.all()) if (
                game.stage == 'showdown' or game.stage == 'svara') else None
    computer_score = calculate_points(computer_hand.cards.all()) if (
                game.stage == 'showdown' or game.stage == 'svara') else None

    context = {
        'game': game,
        'your_hand': your_hand,
        'computer_hand': computer_hand,
        'dark_bet': dark_bet,
        'min_bet': min_bet,
        'svara_entry_fee': svara_entry_fee,
        'your_score': your_score,  # Добавяме твоите точки
        'computer_score': computer_score  # Добавяме точките на компютъра
    }

    if game.stage == 'pre_bet':
        if request.method == 'POST':
            action = request.POST.get('action')
            bet_input = request.POST.get('bet', '0')
            bet_amount = int(bet_input) if bet_input.isdigit() else 0

            if action == 'dark_bet' and bet_amount <= your_hand.player.chips and bet_amount > 0:
                your_hand.bet = bet_amount
                your_hand.player.chips -= bet_amount
                game.pot += bet_amount
                game.dark_bet = bet_amount
                your_hand.player.save()
                your_hand.save()
                game.stage = 'pre_bet_computer'
                game.save()
            else:
                game.stage = 'betting'
                game.save()
            return redirect('game_view', game_id=game.id)

    elif game.stage == 'pre_bet_computer':
        if dark_bet > 0 and computer_hand.player.chips >= dark_bet * 2:
            bet = dark_bet * 2
            computer_hand.bet = bet
            computer_hand.player.chips -= bet
            game.pot += bet
            game.dark_bet = bet
            computer_hand.player.save()
        game.stage = 'betting'
        game.save()
        return redirect('game_view', game_id=game.id)

    elif game.stage == 'betting':
        if request.method == 'POST':
            action = request.POST.get('action')
            bet_input = request.POST.get('bet', '0')
            bet_amount = int(bet_input) if bet_input.isdigit() else 0

            if action == 'fold':
                your_hand.is_active = False
            elif action == 'bet' and bet_amount <= your_hand.player.chips:
                if dark_bet > 0 and bet_amount < dark_bet * 2:
                    bet_amount = dark_bet * 2
                your_hand.bet += bet_amount
                your_hand.player.chips -= bet_amount
                game.pot += bet_amount
                your_hand.player.save()

            your_hand.save()

            if computer_hand.is_active:
                computer_points = calculate_points(computer_hand.cards.all())
                if dark_bet > 0 and computer_hand.bet == dark_bet:
                    min_bet = your_hand.bet
                    if computer_points >= 25 and computer_hand.player.chips >= min_bet:
                        computer_hand.bet = min_bet
                        computer_hand.player.chips -= (min_bet - dark_bet)
                        game.pot += (min_bet - dark_bet)
                        computer_hand.player.save()
                    else:
                        computer_hand.is_active = False
                elif computer_points >= 25 and computer_hand.player.chips >= 10:
                    bet = min(10, computer_hand.player.chips)
                    computer_hand.bet += bet
                    computer_hand.player.chips -= bet
                    game.pot += bet
                    computer_hand.player.save()
                elif computer_points < 20:
                    computer_hand.is_active = False
                computer_hand.save()

            if (not your_hand.is_active) or (not computer_hand.is_active) or \
                    (your_hand.bet > 0 and computer_hand.bet >= your_hand.bet) or \
                    (computer_hand.bet > 0 and your_hand.bet >= computer_hand.bet):
                game.stage = 'showdown'
                game.save()

            return redirect('game_view', game_id=game.id)

    elif game.stage == 'showdown':
        if your_hand.is_active and computer_hand.is_active:
            your_score = calculate_points(your_hand.cards.all())
            computer_score = calculate_points(computer_hand.cards.all())
            if your_score > computer_score:
                winner = your_hand.player
                winner_name = 'You'
            elif computer_score > your_score:
                winner = computer_hand.player
                winner_name = 'Computer'
            else:
                game.stage = 'svara'
                game.svara_pot = game.pot // 2
                game.pot -= game.svara_pot
                game.save()
                context['svara'] = True
                context['svara_pot'] = game.svara_pot
        elif your_hand.is_active:
            winner = your_hand.player
            winner_name = 'You'
        elif computer_hand.is_active:
            winner = computer_hand.player
            winner_name = 'Computer'
        else:
            winner = None
            winner_name = None

        if winner and game.stage != 'svara':
            winner.chips += game.pot
            winner.save()
        context['winner'] = winner_name

    elif game.stage == 'svara':
        if request.method == 'POST':
            action = request.POST.get('action')
            if action == 'join_svara' and your_hand.player.chips >= game.svara_pot // 2:
                your_hand.player.chips -= game.svara_pot // 2
                game.pot += game.svara_pot // 2
                your_hand.player.save()
                if computer_hand.player.chips >= game.svara_pot // 2:
                    computer_hand.player.chips -= game.svara_pot // 2
                    game.pot += game.svara_pot // 2
                    computer_hand.player.save()
                deck = list(Card.objects.all())
                your_hand.cards.clear()
                computer_hand.cards.clear()
                your_cards = random.sample(deck, 3)
                your_hand.cards.set(your_cards)
                for card in your_cards:
                    deck.remove(card)
                computer_cards = random.sample(deck, 3)
                computer_hand.cards.set(computer_cards)
                game.stage = 'showdown'
                game.save()
            return redirect('game_view', game_id=game.id)

    return render(request, 'game/game.html', context)
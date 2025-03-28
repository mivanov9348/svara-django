from django.shortcuts import render, redirect
from .models import Card, Player, Game, PlayerHand
from .utils import calculate_points, computer_betting_decision, start_new_round, computer_dark_bet_decision
import random

def home(request):
    return render(request, 'game/home.html')

def start_game(request):
    if request.method == 'POST':
        try:
            starting_chips = int(request.POST.get('starting_chips', 100))
            starting_chips = max(50, min(starting_chips, 1000))
            min_bet = int(request.POST.get('min_bet', 5))
            min_bet = max(1, min(min_bet, 50))
        except (ValueError, TypeError):
            starting_chips = 100
            min_bet = 5

        Player.objects.all().delete()
        Game.objects.all().delete()
        PlayerHand.objects.all().delete()

        you = Player.objects.create(name='You', chips=starting_chips)
        computer = Player.objects.create(name='Computer', chips=starting_chips)

        deck = list(Card.objects.all())
        if not deck:
            for rank, _ in Card.RANKS:
                for suit, _ in Card.SUITS:
                    Card.objects.create(rank=rank, suit=suit)
            deck = list(Card.objects.all())

        game = Game.objects.create(dealer=you, stage='dark_bet', pot=0, next_player=computer, min_bet=min_bet)  # Задаваме min_bet
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
    min_bet = max(game.dark_bet * 2, computer_hand.bet) if game.dark_bet > 0 else game.min_bet  # Минималният залог е game.min_bet
    svara_entry_fee = game.svara_pot // 2 if hasattr(game, 'svara_pot') and game.svara_pot > 0 else 0

    your_score = calculate_points(your_hand.cards.all()) if game.stage != 'dark_bet' else None
    computer_score = calculate_points(computer_hand.cards.all()) if game.stage in ['showdown', 'svara'] else None

    context = {
        'game': game,
        'your_hand': your_hand,
        'computer_hand': computer_hand,
        'dark_bet': game.dark_bet,
        'min_bet': min_bet,
        'svara_entry_fee': svara_entry_fee,
        'your_score': your_score,
        'computer_score': computer_score,
        'computer_message': '',
    }

    # Stage: Dark Betting
    if game.stage == 'dark_bet':
        if game.next_player == your_hand.player and request.method == 'POST':
            action = request.POST.get('action')
            if action == 'dark_bet':
                bet_input = request.POST.get('bet', '0')
                bet_amount = int(bet_input) if bet_input.isdigit() else 0
                # Уверете се, че залогът е кратен на game.min_bet и не по-малък от минималния
                if bet_amount > 0 and bet_amount <= your_hand.player.chips and bet_amount % game.min_bet == 0:
                    if game.dark_bet > 0 and bet_amount < game.dark_bet * 2:
                        bet_amount = game.dark_bet * 2
                    if bet_amount >= game.min_bet:  # Проверяваме дали е поне минималния залог
                        your_hand.bet = bet_amount
                        your_hand.player.chips -= bet_amount
                        game.pot += bet_amount
                        game.dark_bet = bet_amount
                        game.next_player = computer_hand.player
                        your_hand.player.save()
                        your_hand.save()
            elif action == 'skip':
                game.stage = 'betting'
                game.next_player = your_hand.player if game.dealer == computer_hand.player else computer_hand.player
            game.save()
            return redirect('game_view', game_id=game.id)
        elif game.next_player == computer_hand.player:
            action, bet, message = computer_dark_bet_decision(computer_hand, game)
            context['computer_message'] = message
            if action == 'dark_bet':
                # Уверете се, че залогът на компютъра е кратен на game.min_bet
                bet = max(game.min_bet, (bet // game.min_bet) * game.min_bet)
                if bet <= computer_hand.player.chips:
                    computer_hand.bet = bet
                    computer_hand.player.chips -= bet
                    game.pot += bet
                    game.dark_bet = bet
                    game.next_player = your_hand.player
                    computer_hand.player.save()
                    computer_hand.save()
            else:
                game.stage = 'betting'
                game.next_player = your_hand.player if game.dealer == computer_hand.player else computer_hand.player
            game.save()
            return redirect('game_view', game_id=game.id)

    # Stage: Betting
    elif game.stage == 'betting':
        if game.next_player == your_hand.player and request.method == 'POST':
            action = request.POST.get('action')
            if action == 'bet':
                bet_input = request.POST.get('bet', '0')
                bet_amount = int(bet_input) if bet_input.isdigit() else 0
                # Уверете се, че залогът е кратен на game.min_bet и не по-малък от минималния
                if bet_amount <= your_hand.player.chips and bet_amount > computer_hand.bet and bet_amount % game.min_bet == 0 and bet_amount >= min_bet:
                    additional_bet = bet_amount - your_hand.bet
                    your_hand.bet = bet_amount
                    your_hand.player.chips -= additional_bet
                    game.pot += additional_bet
                    game.next_player = computer_hand.player
                    your_hand.player.save()
            elif action == 'call':
                additional_bet = computer_hand.bet - your_hand.bet
                if additional_bet > 0 and your_hand.player.chips >= additional_bet:
                    your_hand.bet = computer_hand.bet
                    your_hand.player.chips -= additional_bet
                    game.pot += additional_bet
                    your_hand.player.save()
                game.stage = 'showdown' if your_hand.bet == computer_hand.bet else 'betting'
                game.next_player = computer_hand.player
            elif action == 'fold':
                your_hand.is_active = False
                game.stage = 'showdown'
            your_hand.save()
            game.save()
            return redirect('game_view', game_id=game.id)
        elif game.next_player == computer_hand.player and computer_hand.is_active:
            action, bet, message = computer_betting_decision(computer_hand, game, your_hand.bet)
            context['computer_message'] = message
            if action == 'fold':
                computer_hand.is_active = False
                game.stage = 'showdown'
            elif action == 'bet':
                # Уверете се, че залогът на компютъра е кратен на game.min_bet
                bet = max(min_bet, (bet // game.min_bet) * game.min_bet)
                additional_bet = bet - computer_hand.bet
                if additional_bet > 0 and computer_hand.player.chips >= additional_bet:
                    computer_hand.bet = bet
                    computer_hand.player.chips -= additional_bet
                    game.pot += additional_bet
                    computer_hand.player.save()
                game.next_player = your_hand.player
            computer_hand.save()
            game.save()
            if your_hand.bet == computer_hand.bet or not computer_hand.is_active:
                game.stage = 'showdown'
                game.save()
            return redirect('game_view', game_id=game.id)

    # Stage: Showdown
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
        elif your_hand.is_active:
            winner = your_hand.player
            winner_name = 'You'
        elif computer_hand.is_active:
            winner = computer_hand.player
            winner_name = 'Computer'
        else:
            winner = None
            winner_name = None
        if game.dark_bet > 0 and not your_hand.is_active and not computer_hand.is_active:
            winner = game.dealer if game.dealer.bet == game.dark_bet else game.next_player
            winner_name = winner.name
        if winner and game.stage != 'svara':
            winner.chips += game.pot
            winner.save()
            context['winner'] = winner_name
            if start_new_round(game):
                return redirect('game_view', game_id=game.id)
            else:
                context['game_over'] = True
                context['winner'] = f"{winner_name} wins the game!"

    # Stage: Svara
    elif game.stage == 'svara':
        if request.method == 'POST' and request.POST.get('action') == 'join_svara':
            if your_hand.player.chips >= svara_entry_fee:
                your_hand.player.chips -= svara_entry_fee
                game.pot += svara_entry_fee
                your_hand.player.save()
                if computer_hand.player.chips >= svara_entry_fee and random.random() > 0.3:
                    computer_hand.player.chips -= svara_entry_fee
                    game.pot += svara_entry_fee
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
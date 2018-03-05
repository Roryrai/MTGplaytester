###############################################################################
#                                                                             #
#                                MTG PLAYTESTER                               #
#                                                                             #
###############################################################################

#------------------------------------------------------------------------------
# This program is designed to simulate a game of Magic, using a provided deck.
# The program will be given a decklist, in the form of a text file, at runtime,
# which it will load into card objects to use in the playtester. From there,
# the user is able to use different commands to control the game.
#
#
# DECKLIST FILE FORMAT
#
# The decklist must be in a very specific format in order for the playtester
# to correctly identify the different fields of the card. Fields must be
# semicolon-delimited, in the order:
#
# number;name;cost;type;subtype;power;toughness;text
# 
# Mana cost is case sensitive. Cost MUST be provided in uppercase in order to
# be recognized.
#
# For commander decks, replace the integer value of <number> with the word
# "Commander" for the commander only. Other cards must have a value of 1 unless
# they are basic lands.
#
# Fields may be left blank, this will leave the field blank in the card object.
#
# 1;Island;;Basic Land;Island;;;
#
# Here the fields for cost, power, toughness, and text are left empty because
# basic Islands can't have those.
#
# An additional two fields may follow the text field. These fields will be
# to indicate split and transform cards. The full line looks like this:
#
# number;name;cost;type;subtype;power;toughness;text;TRANSFORM;otherhalf
# or
# number;name;cost;type;subtype;power;toughness;text;SPLIT;otherhalf
#
# Replace otherhalf with the full name of the other half of the card. Place the
# first half first in the decklist file, otherwise the program may build the
# transform or split card backwards.
#
# Within the rules text field, use a single backslash followed by a space "\ "
# to indicate a newline at that point in the card.
# Because the fields are semicolon-delimited, spaces and commas in card names
# will be recognized normally.
#
#
# RUNNING THE PLAYTESTER
#
# The playtester is run at the command line by typing
#
# python ./play.py <decklist.deck>
# or, for debugging,
# python ./play.py debug <decklist.deck>
#
# Debug mode prevents the playtester from clearing the console every time
# the boardstate gets updated, allowing any other output to be viewed.
#
# USING THE PLAYTESTER
#
# Most commands are of the form <command> <args> <cardname>. Additionally, a
# number may be specified after a card name to indicate that the command is to
# be performed on the nth applicable card, where n is the number specified.
# Full documentation for commands can be found in the command function, under
# the header "Actual program"
#
# KNOWN ISSUES
#
# Power and toughness need to not go below 0 internally, not just on display
# Add a "damage" command and damage tracking on each turn
#------------------------------------------------------------------------------

from card import Card
from card import ZoneError
from card import CardNotFoundError
from card import CommandError
import random
import sys
import subprocess
import re

# Debug mode
debug = False

# Number of cards allowed in the deck
DECK_SIZE = 60

# Self explanatory
GAME_OVER = False

# Names of the two players
player1 = "P1"
player2 = "P2"

# Life, poison, and commander damage
p1Life = 0
p1Poison = 0
p1Commander = 0
p2Life = 0
p2Poison = 0
p2Commander = 0

# Has anyone won yet?
p1Win = False
p2Win = False

# Turn count, mulligan count, combat phases
turn = 0
mulls = 0
combat = False

# Is the top of my library revealed?
revealed = False

# Number of times a commander has been played from the command zone this game
commandPlayCount = 0

# Lists with the cards in them.
# Most will just get appended to.
# grave will get things insterted
# at index 0 so that it prints
# most recent at the top.
deck = list()
library = list()
field = list()
hand = list()
grave = list()
exiled = list()

# Tokens and emblems
tokens = list()
emblems = list()

# Uh
top = None
bottom = None

# List containing all of the zones from above
zones = (library, field, hand, grave, exiled)

# Not commander by default. This will point
# to the commander card object itself if we
# are playing commander.
commander = False

###############################################################################
#                                                                             #
#                        FUNCTIONS TO MANIPULATE STUFF                        #
#                                                                             #
###############################################################################
    
#------------------------------------------------------------------------------
# Prints the current board state, with a fancy header
#------------------------------------------------------------------------------
def boardstate():
    if not debug:
        subprocess.call("clear", shell=True)
    # Here we build the header of the playtester, which displays
    # information on turn number, as well as life total, poison
    # counters, and possibly commander damage for 2 players.
    
    header()
    
    # Header bar finished, now for the actual board
    printZone(grave, Card.GRAVEYARD)
    printZone(exiled, Card.EXILE)
    printZone(library, Card.LIBRARY)
    printZone(hand, Card.HAND)
    printZone(field, Card.BATTLEFIELD)
    
#------------------------------------------------------------------------------
# Formats a line of text to print in the header bar
#------------------------------------------------------------------------------
def formatHeaderLine(width, string1, string2):
    midpoint = width / 2
    frontWhitespaceLen = (midpoint - len(string1)) / 2
    line = "|"
    for i in range(0, frontWhitespaceLen):
        line += " "
    line += string1
    midWhitespaceLen = (midpoint - len(string2)) / 2 + 1
    for i in range(len(line) - 1, midpoint):
        line += " "
    for i in range(0, midWhitespaceLen):
        line += " "
    line += string2
    for i in range(len(line) - 1, width):
        line += " "
    return line + "|"

#------------------------------------------------------------------------------
# Prints the header for the boardstate
#------------------------------------------------------------------------------
def header():
    # This is the inside width of the box
    width = 70
    # Top border
    line = ""
    line += " "
    for i in range(0, width):
        line += "-"
    print line
    
    # Next line with turn counter
    lineText = "Turn " + str(turn)
    frontWhitespaceLen = (width - len(lineText)) / 2
    line = "|"
    for i in range(0, frontWhitespaceLen):
        line += " "
    line += lineText
    for i in range(len(line) - 1, width):
        line += " "
    print line + "|"
    
    # Second line, this has names on it
    line = formatHeaderLine(width, player1, player2)
    print line
    
    # Third line has life totals on it
    line = formatHeaderLine(width, "L: " + str(p1Life), "L: " + str(p2Life))
    print line
    
    # Fourth line is poison counters
    line = formatHeaderLine(width, "P: " + str(p1Poison), "P: " + str(p2Poison))
    print line
    
    # Optional last line for commander damage
    if commander:
        line = formatHeaderLine(width, "C: " + str(p1Commander), "C: " + str(p2Commander))
        print line
        # If the commander is in the command zone
        if commander.zone() == Card.COMMAND:
            string = commander.name()
            if commandPlayCount > 0:
                string += " (" + str(commandPlayCount) + ")"
            line = formatHeaderLine(width, string, "")
            print line
    # Bottom border
    line = ""
    line += " "
    for i in range(0, width):
        line += "-"
    print line

#------------------------------------------------------------------------------
# Gets a card from the necessary part of the args array. Names in double
# quotes should be matched exactly, otherwise check if the passed string
# is a part of a card name. For instance, <bolt> would match all cards with
# "bolt" in their name, but <"Lightning Bolt"> would match only Lightning Bolt.
# If a type name is passed to getCard, it will return that type name. If the
# string "card" is passed in, getCard returns the first card in the given zone.
# This is primarily useful for moving cards out of the graveyard, hand, or
# exile quickly. Using it if the zone is field is undefined as the battlefield
# does not get printed in the order that cards appear in the list.
# Additionally, if the top card of your library is revealed and has the same
# name as a card in your hand, getCard will default to the top card of your
# library instead of the card in your hand. Most of the time this is a good
# thing. If not, the Move command can be used instead.
#------------------------------------------------------------------------------
def getCard(args, zone=deck, cmd=None):
    # Skip up to a certain number of cards. Skip should be the last item in args.
    try:
        skip = int(args[-1]) - 1
        if skip < 0:
            skip = 0
        cardname = " ".join(args[:-1])
    except ValueError:
        skip = 0
        # This is the card name they passed in
        cardname = " ".join(args)
    # Generic card?
    if cardname == "card" and zone:
        return zone[0]
    # Are we getting a card type?
    for typeName in Card.TYPES:
        if cardname.lower() == typeName.lower() and typeName != Card.EMBLEM:
            # We can return any typename that's not Emblem, since you can't
            # interact with those once they're on the field.
            return typeName

    # If we don't need a specific zone, just get the first instance
    # of the card in the deck. Mostly useful for viewing.
    if not zone:
        raise CardNotFoundError(cardname)
    
    # Special case for when the top card of the library is playable
    if revealed and zone == hand and cmd == "play":
        if cardname.startswith("\"") and cardname.endswith("\"") and len(cardname) > 2:
            if cardname[1:-1] == library[0].name():
                return library[0]
        elif cardname in library[0].name().lower():
            return library[0]
    
    # The card we'll return
    ret = None
    # This was going to get used to check if a given string
    # matched a unique card name but I never got around to making it work
    valid = True
    if cardname.startswith("\"") and cardname.endswith("\"") and len(cardname) > 2:
        # Got a double quoted string so they want an exact match
        # Cut off the quotes
        cardname = cardname[1:-1]
        for card in zone:
            # Look at each card and see if the names match. Ignore case.
            if cardname.lower() == card.name().lower():
                if skip == 0:
                    # If we've skipped the right number
                    # of cards then we're done
                    ret = card
                    break
                else:
                    # Still need to skip some more
                    skip -= 1
                    # Save this card anyways, since it matched, and
                    # there might not be enough matches in the deck
                    ret = card
    else:
        # No quotes, just see if the given string is in the name
        for card in zone:
            # Same stuff as above
            if cardname.lower() in card.name().lower():
                # Look at me trying to make sure I only return
                # a unique card and failing
                #if ret and card.name() != ret.name():
                #    valid = False
                if skip == 0:
                    ret = card
                    break
                else:
                    skip -= 1
                    ret = card
    # If we found a card (ideally a unique card) return it
    if ret and valid:
        return ret
    raise CardNotFoundError(cardname)

#------------------------------------------------------------------------------
# Gets the actual name of a zone from a string. Tests to see if the given
# string is in a zone name and returns the zone name if it is. A zone will only
# be returned if there is only a single possibility. If more than one zone fits
# the input string, the function will return None.
#------------------------------------------------------------------------------
def getZoneNameFromString(string):
    string = string.lower()
    ret = None
    valid = True
    
    for zone in Card.ZONES:
        if string.lower() in zone.lower():
            if ret:
                valid = False
            ret = zone
    # Only return if we didn't match more than one zone
    if valid:
        return ret
    return None

#------------------------------------------------------------------------------
# Loads the decklist from a text file specified
# filename = file to load the deck from
#------------------------------------------------------------------------------
def load(filename):
    global commander
    global DECK_SIZE
    list = open(filename)
    # Each line will contain a single card's information
    for line in list:
        info = line.split(";")
        # Try/catch an index error in case some fields are missing
        try:
            if info[0] == "Commander":
                commander = True
                DECK_SIZE = 100
                cardCount = 1
            else:
                try:
                    cardCount = int(info[0])
                    # Can't have less than 1 of a card
                    if cardCount < 1:
                        raise ValueError
                except ValueError:
                    # Error if invalid card count
                    print "Invalid card count for " + info[1]
                    sys.exit(1)
            name = info[1]
            cost = info[2]
            type = info[3]
            subtype = info[4]
            power = info[5]
            toughness = info[6]
            text = info[7]
        except IndexError:
            print "Index out of bounds on " + name
            sys.exit(1)
        # Make cardCount copies of the new card
        for i in range(0, cardCount):
            # Whether to add the card to the deck or not (for split or transform cards)
            append = True
            # If there are 11 tokens, we have a special case
            # because the card is either a split card or a transform card
            if len(info) == 10:
                # Create the new card, giving it the name of the other
                # card object it will have to link to
                newCard = Card(name, cost, type, subtype, power, toughness, text, info[9].rstrip())
                # It should be either a TRANSFORM card or a SPLIT card.
                # Both halves of each are treated the same for now.
                if info[8] == "TRANSFORM":
                    # Mark this as a transform card
                    newCard.setTransform()
                    frontFace = info[9].rstrip()
                    # Loop over each existing card in the deck.
                    # Testing to see if those cards are the front face
                    # of the new transform card.
                    for card in deck:
                        # If a card is the front face, it will have the same name.
                        # If it's not already linked to a card, then we can link these
                        # two together.
                        if card.name() == frontFace and not card.linked():
                            card.linkBackSide(newCard)
                            # If this new card got linked to another one, it's a secondary
                            # card (the back face of a transform) and shouldn't appear
                            # in the decklist.
                            append = False
                            break
                elif info[8] == "SPLIT":
                    # Pretty much the same thing here except replace transform with split
                    newCard.setSplit()
                    firstHalf = info[9].rstrip()
                    for card in deck:
                        if card.name() == firstHalf and not card.linked():
                            card.linkBackSide(newCard)
                            append = False
                            break
            # This case is the default case
            elif len(info) == 8:
                newCard = Card(name, cost, type, subtype, power, toughness, text, None)
            # If the card is a commander, then mark it as a commander. It still goes in the
            # deck but it won't go in the library normally this way.
            else:
                print "Invalid card syntax for " + info[1]
                sys.exit(1)
            if info[0] == "Commander":
                newCard.setCommander()
                commander = newCard
            # Commander decks can't have duplicates of cards that aren't
            # basic lands so check for that here.
            if commander and not Card.BASIC in newCard.type():
                for card in deck:
                    if newCard.name() == card.name():
                        print "Duplicate of " + newCard.name()
                        sys.exit(1)
            # Finally, add the card to the deck
            if append:
                deck.append(newCard)
                if not newCard.commander():
                    library.append(newCard)
            if "token" in newCard.rulestext():
                buildTokens(newCard.rulestext())
            if "emblem" in newCard.rulestext():
                buildEmblem(newCard)
    # If the deck is not equal to the deck size (either 60 or 100) exit
    if len(deck) != DECK_SIZE:
        print "Deck list must be " + str(DECK_SIZE) + " cards, you had " + str(len(deck))
        sys.exit(1)

#------------------------------------------------------------------------------
# Generates a token based on rulestext in a card.
#------------------------------------------------------------------------------
def buildTokens(text):
    power = None
    toughness = None
    color = ""
    type = ""
    subtype = ""
    rulestext = ""

    # Get power/toughness
    ptPattern = re.compile("X?[0-9]+/X?[0-9]+")
    match = ptPattern.search(text)
    if match:
        ptString = match.group(0)
        power = int(ptString.split("/")[0])
        toughness = int(ptString.split("/")[1])
    # Get color
    colorPattern = re.compile("white|blue|black|red|green|colorless (and white|blue|black|red|green)?")
    match = colorPattern.search(text)
    if match:
        colorString = match.group(0).split(" and ")
        color = colorString[0]
        if len(colorString) == 2:
            color2 = colorString[1]
            color = color + " " + color2
    
    # Get types
    typePattern = re.compile("(legendary)? ([A-Z]{1}[a-z]* )+(enchantment|artifact|creature){1,2} token")
    match = typePattern.search(text)
    if match:
        typeString = match.group(0).split(" ")
        typeString.remove("token")
        typeString.remove("")
        if typeString[0] == "legendary":
            type += "Legendary "
            typeString = typeString[1:]
        type += "Token"
        if Card.ENCHANTMENT.lower() in typeString:
            type += " " + Card.ENCHANTMENT
            typeString.remove(Card.ENCHANTMENT.lower())
        if Card.ARTIFACT.lower() in typeString:
            type += " " + Card.ARTIFACT
            typeString.remove(Card.ARTIFACT.lower())
        if Card.CREATURE.lower() in typeString:
            type += " " + Card.CREATURE
            typeString.remove(Card.CREATURE.lower())
        subtype = " ".join(typeString)
    
    # Get rulestext
    textPattern = re.compile("with [a-z]* onto the battlefield")
    match = textPattern.search(text)
    if match:
        textString = match.group(0).split(" ")
        textString.remove("with")
        textString.remove("onto")
        textString.remove("the")
        textString.remove("battlefield")
        rulestext = " ".join(textString)
        rulestext = rulestext[0].upper() + rulestext[1:]
    # Build the token
    if power and toughness and color and type and subtype:
        newToken = Card(subtype, "", type, subtype, power, toughness, rulestext, None)
        # Check if a token with the same attributes already exists.
        # Prevents making 3 copies of an Elspeth token.
        valid = True
        for token in tokens:
            if token.name() == newToken.name() and token.color() == newToken.color() and \
                    token.power() == newToken.power() and token.toughness() == newToken.toughness() and \
                    token.rulestext == newToken.rulestext():
                valid = False
        if valid:
            tokens.append(newToken)

#------------------------------------------------------------------------------
# Generates an emblem based on rulestext in a card.
#------------------------------------------------------------------------------   
def buildEmblem(walker):
    name = "Emblem - " + walker.name()
    type = "Emblem"
    subtype = walker.name().split(" ")[0]
    if subtype.endswith(","):
        subtype = subtype[:-1]
    text = ""
    textPattern = re.compile('".+?"( and \".*\")*')
    match = textPattern.search(walker.rulestext())
    if match:
        textString = match.group(0).split("\" and \"")
        lines = list()
        for line in textString:
            if line.startswith("\""):
                line = line[1:]
            if line.endswith("\""):
                line = line[:-1]
            lines.append(line)
        emblemText = ".\ ".join(lines)
        emblem = Card(name, "", type, subtype, None, None, emblemText, None)
        emblems.append(emblem)

#------------------------------------------------------------------------------
# Prints a copy of the decklist
#------------------------------------------------------------------------------
def printDecklist():
    for card in deck:
        sys.stdout.write(card.name())
        for i in range(len(card.name()), 40):
            sys.stdout.write(" ")
        print card.type()
    sys.exit()

#------------------------------------------------------------------------------
# Prints all cards in your library
#------------------------------------------------------------------------------
def printLibrary():
    for card in library:
        sys.stdout.write(card.name())
        for i in range(len(card.name()), 40):
            sys.stdout.write(" ")
        print card.type()
    sys.exit()

#------------------------------------------------------------------------------
# Prints cards in a specified zone. Only call with zones and lists that match
# or it will print weird things.
#------------------------------------------------------------------------------
def printZone(zoneList, zoneName):
    global revealed
    cardlist = ""
    # Don't print cards in the library. That would be cheating.
    if zoneName == Card.LIBRARY:
        for card in field:
            if "Play with the top card of your library revealed." in card.rulestext() and not cardlist:
                if library:
                    revealed = True
                    cardlist += library[0].name() + "\n"
                    break
                else:
                    revealed = False
                    cardlist += "Empty"
            else:
                revealed = False
    else:
        # If we're supposed to print the battlefield we have
        # a lot of special cases to deal with
        if zoneName == Card.BATTLEFIELD:
            # We want to sort the field by type, here's a list
            # to store types we've printed already so we don't
            # print artifact creatures and other two-type cards
            # multiple times.
            used = list()
            # Loop over the types, the list in Card.TYPES is in
            # the order we want things to print in.
            for type in Card.TYPES:
                # Do cards of this type exist on the field yet?
                exist = False
                # Now look through each card on the battlefield
                for card in zoneList:
                    # As far as we know we haven't printed this
                    # card yet. Could be wrong though.
                    printed = False
                    if type in card.type():
                        # Here we know we're looking at a card
                        # that has the type we want to print
                        for usedType in used:
                            if usedType in card.type():
                                # If one of its types has been
                                # printed already, then skip it
                                printed = True
                        if not printed:
                            # Indicate tapped cards with a T
                            if card.tapped():
                                cardlist += "T"
                            else:
                                cardlist += " "
                            if card.summonSick():
                                cardlist += "S"
                            else:
                                cardlist += " "
                            cardlist += "  "
                            # Here's the card name finally
                            cardlist += card.name()
                            # Creatures are special, they have
                            # power and toughness on them
                            if type == Card.CREATURE:
                                # Some whitespace for nicer formatting.
                                # Or something like that.
                                for i in range(len(card.name()), Card.width - 5):
                                    cardlist += " "
                                # Dunno why I don't just copy the dynamic box
                                # code from the card image...
                                if card.power() < 10:
                                    cardlist += " "
                                cardlist += str(card.power()) + "/" + str(card.toughness())
                                # Creatures can also have counters
                                if card.counters() > 0:
                                    cardlist += "  " + str(card.counters()) + "c"
                            else:
                                # And so can everything else. Those ones just don't
                                # have power and toughness, so they get whitespace
                                # instead.
                                if card.counters() > 0:
                                    for i in range(len(card.name()), Card.width + 1):
                                        cardlist += " "
                                    cardlist += str(card.counters()) + "c"
                            cardlist += "\n"
                            # We just printed a card so cards of this
                            # type must exist
                            exist = True
                # If cards of this type exist, we want a newline
                # to separate them from cards of a different type
                if exist:
                    cardlist += "\n"
                # Regardless of whether this type appeared on the
                # field or not, we've now used it. Don't print
                # cards with this type again.
                used.append(type)
        elif zoneName == Card.HAND:
            # For cards in hand, indicate their type name
            for card in hand:
                i = 0
                for type in Card.TYPES:
                    if type in card.type():
                        cardlist += type[0]
                        i += 1
                for j in range(i, 4):
                    cardlist += " "
                cardlist += card.name() + "\n"

        else:
            # Cards not on the battlefield are really easy.
            for card in zoneList:
                cardlist += card.name()
                cardlist += "\n"
    print zoneName + " (" + str(len(zoneList)) + "):"
    print cardlist

#------------------------------------------------------------------------------
# Reset the program for a new game
#------------------------------------------------------------------------------
def reset():
    global p1Life
    global p1Poison
    global p1Commander
    global p2Life
    global p2Poison
    global p2Commander
    global p1Win
    global p2Win
    global GAME_OVER
    global turn
    global mulls
    global commandPlayCount
    
    if commander:
        p1Life = 40
        p2Life = 40
        commander.move(Card.COMMAND)
    else:
        p1Life = 20
        p2Life = 20
    p1Poison = 0
    p2Poison = 0
    p1Commander = 0
    p2Commander = 0
    p1Win = False
    p2Win = False
    turn = 0
    mulls = 0
    commandPlayCount = 0
    
    GAME_OVER = False
    reshuffle()
    draw(7)
    turn += 1
    boardstate()

#------------------------------------------------------------------------------
# Reshuffle all cards in all zones back into the library
#------------------------------------------------------------------------------
def reshuffle():
    global library
    del library[:]
    del hand[:]
    del grave[:]
    del exiled[:]
    del field[:]
    for card in deck:
        if not card.commander():
            card.move(Card.LIBRARY)
            library.append(card)
    shuffle()

###############################################################################
#                                                                             #
#                          FUNCTIONS TO PLAY THE GAME                         #
#                                                                             #
###############################################################################

#------------------------------------------------------------------------------
# Checks if the game is over or not. Listed first because it doesn't modify
# the game state like all the other functions.
#------------------------------------------------------------------------------
def checkVictory():
    global p1Win
    global p2Win
    global GAME_OVER
    if p1Win:
        GAME_OVER = True
        print "Player 1 win"
    if p2Win:
        GAME_OVER = True
        print "Player 2 win"

#------------------------------------------------------------------------------
# Handles state-based actions, like creatures dying if they have zero toughness
# or planeswalkers dying if they have no loyalty counters on them.
#------------------------------------------------------------------------------
def stateBased():
    removing = list()
    for card in field:
        # Kill creatures with 0 toughness
        if Card.CREATURE in card.type() and card.toughness() == 0:
            removing.append(card)
        # Kill planeswalkers with 0 counters
        if Card.PLANESWALKER in card.type() and card.counters() == 0:
            removing.append(card)
    for card in removing:
        kill(card)

#------------------------------------------------------------------------------
# Applies an anthem to all applicable creatures.
#------------------------------------------------------------------------------
def anthem(card):
    anthemType = card.anthemType()
    anthemPower = card.anthemPower()
    anthemToughness = card.anthemToughness()
    anthemKeywords = card.anthemKeywords()
    for thing in field:
        if "Other" in anthemType and thing == card:
            continue
        for type in anthemType:
            typeInThingType = type.lower() in thing.type().lower()
            typeInThingSubtype = type.lower() in thing.subtype().lower()
            typeInThingColor = type.lower() in thing.color().lower()
            #thingIsCreature = Card.CREATURE in thing.type()
            
            thingIsAffected = typeInThingType or typeInThingSubtype or typeInThingColor
            #andWithLast = orFirstThree and thingIsCreature
            if thingIsAffected:
                thing.anthemPowerBonus(anthemPower)
                thing.anthemToughnessBonus(anthemToughness)
                thing.anthemKeywordMod(anthemKeywords)
                break

#------------------------------------------------------------------------------
# Applies anthems to all applicable creatures.
#------------------------------------------------------------------------------
def applyAnthems():
    for card in field:
        card.resetAnthem()
    for card in field:
        if card.anthem():
            anthem(card)

#------------------------------------------------------------------------------
# Attacks with all creatures in the list attackers. Creatures are assumed to be
# under player one's control and damage is dealt to player two.
#------------------------------------------------------------------------------
def attack(attackers):
    # Total non-commander damage
    total = 0
    # Total commander damage
    totalCommander = 0
    # Total poison damage
    poison = 0
    # Loop through attacking creatures
    for creature in attackers:
        damage = creature.power()
        if Card.DOUBLESTRIKE in creature.keywords():
            damage += creature.power()
        # Handle non-infect damage first, it's much more common.
        if not Card.INFECT in creature.keywords():
            if creature == commander:
                totalCommander += damage
            else:
                total += damage
        else:
            # For all you nasty people who play infect decks.
            # Commanders with infect don't deal commander damage
            # so there's no extra check.
            poison += damage
        if Card.VIGILANCE not in creature.keywords():
            creature.tap()
    # Gotten all the damage totals by here, time to apply them.
    modStat("p2", "life", -1*total)
    modStat("p2", "poison", poison)
    modStat("p2", "commander", totalCommander)

#------------------------------------------------------------------------------
# Returns a card from the battlefield to your hand.
#------------------------------------------------------------------------------
def bounce(card):
    if card in Card.TYPES:
        type = card
        remove = list()
        for thing in field:
            if type in thing.type():
                thing.move(Card.HAND)
                remove.append(thing)
        for thing in remove:
            field.remove(thing)
            if not Card.TOKEN in thing.type():
                hand.append(thing)
    else:
        card.move(Card.HAND)
        field.remove(card)
        if not Card.TOKEN in card.type():
            hand.append(card)

#------------------------------------------------------------------------------
# Creates a token that's a copy of a card on the field.
#------------------------------------------------------------------------------
def copy(card):
    token = card.copy()
    field.append(token)

#------------------------------------------------------------------------------
# Adds n counters to a card. n can be negative
#------------------------------------------------------------------------------
def counters(n, card):
    if card in Card.TYPES:
        type = card
        for thing in field:
            if type in thing.type():
                thing.modCounters(n)
    else:
        card.modCounters(n)

#------------------------------------------------------------------------------
# Discard a card from your hand
#------------------------------------------------------------------------------
def discard(card):
    card.discard()
    hand.remove(card)
    grave.insert(0, card)

#------------------------------------------------------------------------------
# Draw a number of cards
# number = number of cards to draw
#------------------------------------------------------------------------------
def draw(number):
    try:
        for i in range(0, number):
            card = library.pop(0)
            card.draw()
            hand.append(card)
    except IndexError:
        p2Win = True

#------------------------------------------------------------------------------
# Ends your turn. This resets until end of turn modifiers, without advancing
# the turn counter, untapping things, or drawing a card.
#------------------------------------------------------------------------------       
def endTurn():
    for card in field:
        card.endTurn()

#------------------------------------------------------------------------------
# Exiles a card in play
# card = card to exile
#------------------------------------------------------------------------------
def exile(card):
    if card in Card.TYPES:
        type = card
        remove = list()
        for thing in field:
            if type in thing.type():
                thing.move(Card.EXILE)
                remove.append(thing)
        for thing in remove:
            field.remove(thing)
            if not Card.TOKEN in thing.type() and thing != commander:
                exiled.insert(0, thing)
    else:
        card.move(Card.EXILE)
        field.remove(card)
        if not Card.TOKEN in card.type() and card != commander:
            exiled.insert(0, card)

#------------------------------------------------------------------------------
# Fetches a card from your library to your hand.
#------------------------------------------------------------------------------
def fetch(args):
    move(Card.LIBRARY, Card.HAND, cardArgs=args)

#------------------------------------------------------------------------------
# Destroys a card in play
# card = card to destroy
#------------------------------------------------------------------------------
def kill(card):
    if card in Card.TYPES:
        type = card
        remove = list()
        for thing in field:
            if type in thing.type():
                if not Card.INDESTRUCTIBLE in thing.keywords():
                    thing.move(Card.GRAVEYARD)
                    remove.append(thing)
        for thing in remove:
            field.remove(thing)
            if not Card.TOKEN in thing.type() and thing != commander:
                grave.insert(0, thing)
    else:
        if not Card.INDESTRUCTIBLE in card.keywords():
            card.move(Card.GRAVEYARD)
            field.remove(card)
            if not Card.TOKEN in card.type() and card != commander:
                grave.insert(0, card)

#------------------------------------------------------------------------------
# Causes a player to lose an amount of life.
#------------------------------------------------------------------------------    
def modStat(player, stat, number):
    global p1Life
    global p2Life
    global p1Poison
    global p2Poison
    global p1Commander
    global p2Commander
    global p1Win
    global p2Win
    if player == "p1":
        if stat == "life":
            p1Life += number
            if p1Life <= 0:
                p2Win = True
        if stat == "poison":
            p1Poison += number
            if p1Poison >= 10:
                p2Win = True
        if stat == "commander":
            p1Commander += number
            p1Life -= number
            if p1Commander > 20:
                p2Win = True
    elif player == "p2":
        if stat == "life":
            p2Life += number
            if p2Life <= 0:
                p1Win = True
        if stat == "poison":
            p2Poison += number
            if p2Poison >= 10:
                p1Win = True
        if stat == "commander":
            p2Commander += number
            p2Life -= number
            if p2Commander > 20:
                p1Win = True
    else:
        raise CommandError

#------------------------------------------------------------------------------
# Mills the top n cards of your library.
#------------------------------------------------------------------------------
def mill(n):
    for i in range(0, n):
        card = library[0]
        card.move(Card.GRVEYARD)
        library.remove(card)
        grave.insert(0, card)

#------------------------------------------------------------------------------
# Moves a card between zones
#------------------------------------------------------------------------------
def move(fromZone, toZone, cardArgs=None):
    # Get the right value for the from zone
    fromZone = getZoneNameFromString(fromZone)
    # Get the right value for the to zone
    toZone = getZoneNameFromString(toZone)
    
    if not fromZone or not toZone:
        raise ZoneError("Zone does not exist, or zone name is not specific enough.")
    
    # Do we need to shuffle the library after moving the card?
    shuffleLibrary = False
    # So far we don't have a card. Maybe that will change in a minute.
    card = None
    # Change the zone to the corresponding list
    if fromZone == Card.HAND:
        fromZone = hand
    if fromZone == Card.BATTLEFIELD:
        fromZone = field
    if fromZone == Card.EXILE:
        fromZone = exiled
    if fromZone ==  Card.GRAVEYARD:
        fromZone = grave
    if fromZone == Card.LIBRARY:
        fromZone = library
        shuffleLibrary = True
    if fromZone == Card.COMMAND:
        fromZone = None
    if (fromZone == Card.TOP or fromZone == Card.BOTTOM) and cardArgs != None:
        raise ZoneError("Can't move a specific card from top or bottom.")
    # If they want the top card or the bottom card
    if fromZone == Card.TOP or fromZone == Card.BOTTOM:
        # We're taking a card from the library, just a specific index
        # instead of a specific card like the others
        if fromZone == Card.TOP:
            card = library[0]
        if fromZone == Card.BOTTOM:
            card = library[-1]
        fromZone = library
    
    # Get the card if they gave one. We shouldn't be here if we need a card
    # and they didn't give one.
    if cardArgs:
        card = getCard(cardArgs, fromZone)
        
    # Prepare to move the card if it exists
    if card:
        if fromZone:
            # If the place the card is coming from exists as a list
            # in this program (so not the command zone)
            fromZone.remove(card)
            if shuffleLibrary:
                # Simple enough, right?
                shuffle()
        if not Card.TOKEN in card.type():
            # If it's not a token it can go places besides the battlefield.
            # Otherwise it just sort of goes away.
            if toZone == Card.LIBRARY:
                library.append(card)
                shuffle()
            if toZone == Card.TOP:
                toZone = Card.LIBRARY
                library.insert(0, card)
            if toZone == Card.BOTTOM:
                toZone = Card.LIBRARY
                library.append(card)
            if toZone == Card.BATTLEFIELD:
                field.append(card)
            if toZone == Card.HAND:
                hand.append(card)
            if toZone == Card.EXILE:
                exiled.append(card)
            if toZone == Card.GRAVEYARD:
                grave.insert(0, card)
        if toZone == Card.COMMAND and not card.commander():
            # Can't put something that's not the commander in the command zone
            raise ZoneError(card.name() + " can't be put in the command zone.")
        card.move(toZone)
    else:
        raise CardNotFoundError("Card")

#------------------------------------------------------------------------------
# Lets the player mulligan, reshuffling their hand and drawing one fewer cards.
# In commander, the first mulligan is free. You can only mulligan on turn 1.
#------------------------------------------------------------------------------
def mulligan():
    global mulls
    if turn == 1:
        reshuffle()
        mulls += 1
        if commander:
            draw(7 - (mulls -1))
        else:
            draw(7 - mulls)

#------------------------------------------------------------------------------
# Moves to the next turn.
#------------------------------------------------------------------------------
def nextTurn():
    global turn
    endTurn()
    turn += 1
    untapAll()
    # Upkeep
    for card in field:
        card.nextTurn()
    draw(1)
    
#------------------------------------------------------------------------------
# Plays a card from your hand to the battlefield
# card = index of the card to play
#------------------------------------------------------------------------------
def play(card):
    global commandPlayCount
    # Dump all cards of a cretain type at once
    if card in Card.TYPES:
        # Somehow
        pass
    
    else:
        # Until then only play cards that are actual cards
        # Cards can be played if they are in hand, if they are a commander,
        # if they are tokens, or if the top card of your library is revealed
        # and playable.
        if card in hand or card.commander() or Card.TOKEN in card.type() or revealed and library and card == library[0]:
            # If we're playing the commander from the command zone increment count
            if card == commander:
                if card.zone() == Card.COMMAND:
                    commandPlayCount += 1
            # Otherwise remove the card from hand 
            if card in hand:
                hand.remove(card)
            # Or maybe the library
            if library and card == library[0]:
                library.pop(0)
            # Play it
            card.play()
            # Figure out what zone it ended up in and put it there.
            if card.zone() == Card.GRAVEYARD:
                grave.insert(0, card)
            elif card.zone() == Card.EXILE:
                exiled.insert(0, card)
            elif card.zone() == Card.BATTLEFIELD:
                field.append(card)
            elif card.zone() == Card.LIBRARY:
                library.append(card)
                shuffle()
            elif card.zone() == Card.BOTTOM:
                library.append(card)
                card.move(Card.LIBRARY)
            elif card.zone() == Card.TOP:
                library.insert(0, card)
                card.move(Card.LIBRARY)
        else:
            raise ZoneError(card.name() + " needs to be in your hand to play it.")
        
#------------------------------------------------------------------------------
# Adds a +1/+1 counter to the card
#------------------------------------------------------------------------------
def plusone(n, card):
    if card in Card.TYPES:
        type = card
        for thing in field:
            if type in thing.type():
                thing.modPlusOne(n)
    else:
        card.modPlusOne(n)

#------------------------------------------------------------------------------
# Adds n power to a card until end of turn. n can be negative
#------------------------------------------------------------------------------
def power(n, card):
    if card in Card.TYPES:
        type = card
        for thing in field:
            if type in thing.type():
                thing.modPower(n)
    else:
        card.modPower(n)

#------------------------------------------------------------------------------
# Sacrifice a permanent
#------------------------------------------------------------------------------
def sacrifice(card):
    if card in Card.TYPES:
        type = card
        remove = list()
        for thing in field:
            if type in thing.type():
                thing.move(Card.GRAVEYARD)
                remove.append(thing)
        for thing in remove:
            field.remove(thing)
            if not Card.TOKEN in thing.type() and thing != commander:
                grave.insert(0, thing)
    else:
        card.move(Card.GRAVEYARD)
        field.remove(card)
        if not Card.TOKEN in card.type() and card != commander:
            grave.insert(0, card)
#------------------------------------------------------------------------------
# Scry n cards.
#------------------------------------------------------------------------------
def scry(n):
    print "Not yet implemented"
    
#------------------------------------------------------------------------------    
# Shuffle your library
#------------------------------------------------------------------------------
def shuffle():
    random.shuffle(library)

#------------------------------------------------------------------------------
# Taps a card on the battlefield
#------------------------------------------------------------------------------
def tap(card):
    if card in Card.TYPES:
        type = card
        for thing in field:
            if type in thing.type():
                thing.tap()
    else:
        card.tap()
    
#------------------------------------------------------------------------------
# Look at the top n cards of your library, and put them back in any order?
#------------------------------------------------------------------------------
def top(n):
    if n > len(library):
        n = len(library)
    for i in range(0, n):
        print library[i].name()

#------------------------------------------------------------------------------
# Adds n toughness to a card until end of turn. n can be negative
#------------------------------------------------------------------------------
def toughness(n, card):
    if card in Card.TYPES:
        type = card
        for thing in field:
            if type in thing.type():
                thing.modToughness(n)
    else:
        card.modToughness(n)

#------------------------------------------------------------------------------
# Untaps a specific card
# card = card to untap
#------------------------------------------------------------------------------
def untap(card):
    if card in Card.TYPES:
        type = card
        for thing in field:
            if type in thing.type():
                thing.untap()
    else:
        card.untap()

#------------------------------------------------------------------------------
# Untaps all permanents in play. Used for the untap step.
#------------------------------------------------------------------------------
def untapAll():
    for card in field:
        if not card.name() + " doesn't untap during your untap step" in card.rulestext():
            card.untap()

#------------------------------------------------------------------------------
# Print out a requested card
#------------------------------------------------------------------------------
def view(cardArgs):
    boardstate()
    try:
        card = getCard(cardArgs, zone=field)
    except CardNotFoundError:
        card = getCard(cardArgs)
    print card
    
    
    
###############################################################################
#                                                                             #
#                               ACTUAL PROGRAM                                #
#                                                                             #
###############################################################################

#------------------------------------------------------------------------------
# This function deals with I/O for command handling. It checks what command was
# entered and parses arguments appropriately to extract information from the
# user. After doing this, it calls the relevant function, passing it whatever
# it needs to run.
#------------------------------------------------------------------------------
def command(cmd, args):
    global turn
    global combat


#------------------------------------------------------------------------------
# Bounce
#
#         Syntax: bounce <card>
#-------#
        # Returns a card from the battlefield to your hand.
        #----------------------------------------------------------------------
    if cmd == "bounce":
        if args and len(args) >= 1:
            card = getCard(args, field)
            bounce(card)
        else:
            raise CommandError
#------------------------------------------------------------------------------
# Combat
#
#         Syntax: combat <card>
#-------#
        # Attacks with all specified creatures, dealing damage appropriately.
        # You can specify "all" to attack with all creatures.
        #----------------------------------------------------------------------
    if cmd == "combat":
        # Can only attack if we haven't had a combat phase yet. Usually.
        if not combat:
            input = "combat"
            # List of attackers
            attackers = list()
            input = raw_input("Select attackers: ")
            while input != "":
                args = input.split(" ")
                if args[0].lower() == "all" and len(args) == 1:
                    for card in field:
                        # Add all creatures that are not tapped or affected by summoning sickness
                        if Card.CREATURE in card.type() and not card.summonSick() and not card.tapped():
                            # Oh and also that aren't already declared as attackers this turn
                            if card not in attackers:
                                attackers.append(card)
                    # Specified all, no need to wait on input.
                    break
                else:
                    card = getCard(args, field)
                    # Card isn't a creature
                    if not Card.CREATURE in card.type():
                        print card.name() + " isn't a creature."
                    # Card is a creature but has summoning sickness
                    elif card.summonSick():
                        print card.name() + " has summoning sickness and can't attack this turn."
                    # Card is a creature and doesn't have summoning sickness, but is tapped
                    elif card.tapped():
                        print card.name() + " is tapped and can't attack"
                    # Last check, have they already declared this creature as an attacker this turn?
                    elif card not in attackers:
                        attackers.append(card)
                    # Start of the next iteration
                    input = raw_input("Select attackers: ")
            # Assuming that we have attacking creatures this turn,
            # tell them what all they chose and ask for confirmation.
            if attackers:
                # Blank line for pretty output
                print ""
                sys.stdout.write("Attacking with " + str(len(attackers)) + " creature")
                if len(attackers) > 1:
                    sys.stdout.write("s")
                print ":\n"
                for creature in attackers:
                    print creature.name() + " (" + str(creature.power()) + "/" + str(creature.toughness()) + ")"
                # Another blank line for pretty output
                print ""
                input = raw_input("Continue with attack? (y/n): ")
                while input.lower() != "no" and input.lower() != "n":
                    if input.lower() == "y" or input.lower() == "yes":
                        attack(attackers)
                        # Combat step has been used this turn. Gone until extra combat steps can be added.
                        #combat = True
                        return True
                    input = raw_input("Continue with attack? (y/n): ")
            else:
                print "No attackers selected"
                return False
        else:
            print "You've already used your combat step this turn."
            return False

#------------------------------------------------------------------------------
# Copy
#
#         Syntax: copy <card>
#-------#
        # Creates a token that is a copy of a card on the battlefield and puts
        # it onto the battlefield.
        #----------------------------------------------------------------------
    if cmd == "copy":
        if args and len(args) >= 1:
            card = getCard(args, zone=field)
            copy(card)
        else:
            raise CommandError

#------------------------------------------------------------------------------
# Count
#
#         Syntax: count
#-------#
        # Utility function to display how many cards of each type are in the
        # the deck. This will NOT include cards with multiple types in all of
        # the relevant lists. Types are prioritized in the order
        # Creatures, planeswalkers, enchantments, artifacts, lands, instants,
        # and sorceries. For example, artifact creatures will only appear in
        # the count for creatures, not in artifacts, or both. Only the number
        # of cards in each type will be printed, not the cards themselves.
        #----------------------------------------------------------------------
    if cmd == "count":
        if not args:
            print ""
            used = list()
            for type in Card.TYPES:
                number = 0
                for card in deck:
                    counted = False
                    if type in card.type():
                        for usedtype in used:
                            if usedtype in card.type():
                                counted = True
                        if not counted:
                            number += 1
                string = type
                for i in range(len(type), 14):
                    string += " "
                string += str(number)
                print string
            print ""
            return False
        else:
            raise CommandError

#------------------------------------------------------------------------------
# Counters
#
#         Syntax: counters <n> <card>
#-------#
        # Adds n counters to a card.
        #----------------------------------------------------------------------
    if cmd == "counters":
        if args and len(args) >= 2:
            try:
                n = int(args[0])
            except ValueError:
                raise CommandError
            card = getCard(args[1:], zone=field)
            counters(n, card)
        else:
            raise CommandError

#------------------------------------------------------------------------------
# Discard
#
#         Syntax: discard <card>
#-------#
        # Discard a card from your hand.
        #----------------------------------------------------------------------
    if cmd == "discard":
        if args and len(args) >= 1:
            card = getCard(args, zone=hand)
            discard(card)
        else:
            raise CommandError
        
#------------------------------------------------------------------------------
# Do
#
#         Syntax: do <n> <command> <args>
#-------#
        # Repeatedly executes <command> with arguments <args>, up to <n> times.
        #----------------------------------------------------------------------
    if cmd == "do":
        if args:
            try:
                n = int(args[0])
            except ValueError:
                raise CommandError
            thing = args[1]
            args = args[2:]
            do(thing, args, n)
        
#------------------------------------------------------------------------------
# Draw
#
#         Syntax: draw <number>
#-------#
        # Draws <number> cards from the top of your library.
        #----------------------------------------------------------------------
    if cmd == "draw":
        if args and len(args) == 1:
            try:
                draw(int(args[0]))
            except ValueError:
                raise CommandError
        elif not args or len(args) == 0:
            draw(1)
        else:
            raise CommandError

#------------------------------------------------------------------------------
# Emblem
#
#         Syntax: emblem <planeswalker>
#-------#
        # Puts the emblem for the specified planeswalker in play.
        #----------------------------------------------------------------------
    if cmd == "emblem":
        if args and len(args) >= 1:
            card = getCard(args, emblems)
            token = card.copy()
            field.append(token)
            token.move(Card.BATTLEFIELD)
        else:
            raise CommandError

#------------------------------------------------------------------------------
# End
#
#         Syntax: end
#-------#
        # Ends the turn, removing all temporary power/toughness modifiers.
        #----------------------------------------------------------------------
    if cmd == "end":
        if not args:
            endTurn()
        else:
            raise CommandError

#------------------------------------------------------------------------------
# Exile
#
#         Syntax: exile <card>
#-------#
        # Exiles a card in play.
        #----------------------------------------------------------------------
    if cmd == "exile":
        if args and len(args) >= 1:
            card = getCard(args, field)
            exile(card)
        else:
            raise CommandError

#------------------------------------------------------------------------------
# Facedown
#
#         Syntax: facedown <card>
#-------#
        # Turns a face up card face down.
        #----------------------------------------------------------------------
    if cmd == "facedown":
        if args and len(args) >= 1:
            card = getCard(args, field)
            if not card.facedown():
                card.morph()
            else:
                print card.name() + " is already face down."
        else:
            raise CommandError

#------------------------------------------------------------------------------
# Faceup
#
#         Syntax: faceup <card>
#-------#
        # Turns a face down card face up.
        #----------------------------------------------------------------------
    if cmd == "faceup":
        if args and len(args) >= 1:
            card = getCard(args, field)
            if card.facedown():
                card.morph()
                if Card.MEGAMORPH in card.keywords():
                    plusone(1, card)
            else:
                print card.name() + " is already face up."
        else:
            raise CommandError
            
#------------------------------------------------------------------------------
# Fetch
#
#         Syntax: draw <number>
#-------#
        # Fetches a specific card from your library, putting it in your hand.
        #----------------------------------------------------------------------
    if cmd == "fetch":
        if args:
            fetch(args)
        else:
            raise CommandError

#------------------------------------------------------------------------------
# Keywords
#
#         Syntax: <keyword> <card>
#-------#
        # Grants a card a keyword until end of turn.
        #----------------------------------------------------------------------
    if cmd.lower() == "first" or cmd.lower() == "double":
        if args and args[0].lower() == "strike":
            cmd += " strike"
            args = args[1:]
    keyword = cmd.capitalize()
    if keyword in Card.KEYWORDS:
        card = getCard(args, field)
        if card:
            card.modKeywords(keyword)
            boardstate()
            cmd = "keywords"
    if cmd == "keywords":
        if args:
            card = getCard(args, field)
            if card:
                if card.keywords():
                    for keyword in card.keywords():
                        print keyword
                else:
                    print "None"
                return False
        else:
            raise CommandError
                    
#------------------------------------------------------------------------------
# Kill
#
#         Syntax: kill <card>
#-------#
        # Kills a card on the field, sending it to the graveyard.
        #----------------------------------------------------------------------
    if cmd == "kill":
        if args:
            card = getCard(args, zone=field)
            kill(card)
        else:
            raise CommandError

#------------------------------------------------------------------------------
# Load
#
#         Syntax: load <decklist>
#-------#
        # Loads a new decklist into the playtester without having to exit it.
        #----------------------------------------------------------------------
    if cmd == "load":
        global commander
        global DECK_SIZE
        if args and len(args) == 1:
            del deck[:]
            commander = False
            DECK_SIZE = 60
            load(args[0])
            reset()
        else:
            raise CommandError

#------------------------------------------------------------------------------
# Mill
#
#         Syntax: mill <n>
#-------#
        # Mills the top n cards of your library, sending them to the graveyard.
        #----------------------------------------------------------------------
    if cmd == "mill":
        if args and len(args) == 1:
            try:
                mill(int(args[0]))
            except ValueError:
                raise CommandError
        else:
            raise CommandError

#------------------------------------------------------------------------------
# Mod (player stats)
#
#         Syntax: p1 <command> <value>
#-------#
        # Modifies life total, poison counters, or commander damage on a
        # player. Adding commander damage automatically decreases life total.
        #----------------------------------------------------------------------
    if cmd == "p1" or cmd == "p2":
        if args and len(args) == 2:
            try:
                n = int(args[1])
                stat = args[0]
                if stat != "life" and stat != "poison" and stat != "commander":
                    raise ValueError
            except ValueError:
                raise CommandError
            modStat(cmd, stat, n)
        else:
            raise CommandError

#------------------------------------------------------------------------------
# Morph
#
#         Syntax: morph <card>
#-------#
        # Plays a morph card from your hand, face down.
        #----------------------------------------------------------------------
    if cmd == "morph":
        if args and len(args) >= 1:
            card = getCard(args, hand)
            if Card.MORPH or Card.MEGAMORPH in card.keywords():
                play(card)
                card.morph()
            else:
                print card.name() + " doesn't have morph."
        
#------------------------------------------------------------------------------
# Move
#
#         Syntax: <from zone> <to zone> <card>
#-------#
        # Moves the specified card from one zone to another. Legal zones are:
        #    field
        #    hand
        #    grave
        #    exile
        #    library      - Moving a card to library will automatically shuffle
        #       top       - References the top card
        #       bottom    - References the bottom card
        #----------------------------------------------------------------------
    if cmd == "move":
        if args and len(args) >= 2:
            fromZone = args[0]
            toZone = args[1]
            if args and len(args) == 2:
                cardArgs = None
            else:
                cardArgs = args[2:]
            move(fromZone, toZone, cardArgs)
        else:
            raise CommandError

#------------------------------------------------------------------------------
# Mull
#
#         Syntax: mull
#-------#
        # Mulligans your opening hand, drawing one fewer cards than your
        # previous hand size. If playing commander, the first mulligan is free.
        # Additionally, if not playing commander, if a player has to mulligan,
        # he or she will be given the opportunity to scry 1.
        #----------------------------------------------------------------------
    if cmd == "mull":
        if not args:
            mulligan()
        else:
            raise CommandError
            
#------------------------------------------------------------------------------
# Next
#
#         Syntax: next
#-------#
        # Move to the next turn. Untap all permanents and
        # draw a card.
        #----------------------------------------------------------------------
    if cmd == "next":
        if not args:
            nextTurn()
        else:
            raise CommandError
            
#------------------------------------------------------------------------------
# Play
#
#         Syntax: play <card>
#                 cast <card>
#-------#
        # The play command will play a card from the user's hand.
        # The card will automatically move to the correct zone.
        #----------------------------------------------------------------------
    if cmd == "play" or cmd == "cast":
        if args and len(args) >= 1:
            cardname = " ".join(args)
            card = None
            if commander:
                if (cardname.lower() == "commander" or cardname.lower() in commander.name().lower()) \
                        and (commander in hand or commander.zone() == Card.COMMAND):
                    card = commander
            if not card:
                if hand:
                    card = getCard(args, zone=hand, cmd=cmd)
                else:
                    raise ZoneError("You have no cards in hand.")
            if card == commander and (commander.zone() != Card.HAND and commander.zone() != Card.COMMAND):
                raise ZoneError(commander.name() + " can't be played from " + commander.zone())
            play(card)
        else:
            raise CommandError

#------------------------------------------------------------------------------
# Plusone
#
#         Syntax: plusone <card>
#-------#
        # Adds a +1/+1 counter to a creature.
        #----------------------------------------------------------------------
    if cmd == "plusone":
        if args and len(args) >= 2:
            try:
                n = int(args[0])
            except ValueError:
                raise CommandError
            card = getCard(args[1:], zone=field)
            plusone(n, card)
        else:
            raise CommandError
            
#------------------------------------------------------------------------------
# Power
#
#     Syntax: power <n> <card>
#-------#
        # Adds n power to a card. This effect ends at end of turn.
        #----------------------------------------------------------------------
    if cmd == "power":
        if args and len(args) >= 2:
            try:
                n = int(args[0])
            except ValueError:
                raise CommandError
            card = getCard(args[1:], zone=field)
            power(n, card)
        else:
            raise CommandError

#------------------------------------------------------------------------------
# Reset
#
#         Syntax: reset
#-------#
        # Reset the game
        #----------------------------------------------------------------------
    if cmd == "reset":
        reset()
        return False

#------------------------------------------------------------------------------
# Sacrifice
#
#         Syntax: sac <card>
#-------#
        # Sacrifice a permanent you control.
        #----------------------------------------------------------------------
    if cmd == "sac" or cmd == "crack":
        if args:
            card = getCard(args, field)
            sacrifice(card)
        else:
            raise CommandError

#------------------------------------------------------------------------------
# Shuffle
#
#         Syntax: shuffle
#-------#
        # Shuffle your library
        #----------------------------------------------------------------------
    if cmd == "shuffle":
        shuffle()

#------------------------------------------------------------------------------
# Tap
#
#         Syntax: tap <card>
#-------#
        # Taps a single card. Tap will find the first untapped card it can.
        #----------------------------------------------------------------------
    if cmd == "tap":
        if args:
            try:
                # If the last argument is an integer do nothing
                int(args[-1])
                args[-1] = int(args[-1])
            except ValueError:
                # If it's not append 1 to it. Same effect if they 
                # didn't specify an int but it lets us iterate
                # past already tapped cards.
                args.append(1)
            card = getCard(args, field)
            if isinstance(card, Card):
                prev = None
                while card.tapped() and prev != card:
                    prev = card
                    args[-1] += 1
                    card = getCard(args, field)
            tap(card)
        else:
            raise CommandError
            
#------------------------------------------------------------------------------
# Token
#
#         Syntax: token <type>
#-------#
        # Puts a token onto the battlefield.
        #----------------------------------------------------------------------
    if cmd == "token":
        if args and len(args) >= 1:
            card = getCard(args, tokens)
            token = card.copy()
            token.move(Card.BATTLEFIELD)
            field.append(token)
        else:
            raise CommandError
            
#------------------------------------------------------------------------------
# Top
#
#         Syntax: top <n>
#-------#
        # Look at the top n cards of your library, and put them back
        # in any order?
        #----------------------------------------------------------------------
    if cmd == "top":
        if not args:
            n = 3
        elif len(args) == 1:
            try:
                n = int(args[0])
            except ValueError:
                raise CommandError
        else:
            raise CommandError
        top(n)
        return False

#------------------------------------------------------------------------------
# Toughness
#
#         Syntax: toughness <n> <card>
#-------#
        # Adds n toughness to a card. This effect ends at end of turn.
        #----------------------------------------------------------------------
    if cmd == "toughness":
        if args and len(args) >= 2:
            try:
                n = int(args[0])
            except ValueError:
                raise CommandError
            card = getCard(args[1:], field)
            toughness(n, card)
        else:
            raise CommandError

#------------------------------------------------------------------------------
# Transform
#
#         Syntax: transform <card>
#-------#
        # Transforms a flip card.
        #----------------------------------------------------------------------
    if cmd == "transform":
        if args:
            card = getCard(args, field)
            if card.isTransform() and card.zone() == Card.BATTLEFIELD:
                card.transform()
            else:
                print card.name() + " can't transform."
        
#------------------------------------------------------------------------------
# Untap
#
#         Syntax: untap <card>
#-------#
        # Untaps a single card. Untap will find the first untapped card it can.
        #----------------------------------------------------------------------
    if cmd == "untap":
        if args:
            try:
                # If the last argument is an integer do nothing
                int(args[-1])
                args[-1] = int(args[-1])
            except ValueError:
                # If it's not append 1 to it. Same effect if they 
                # didn't specify an int but it lets us iterate
                # past already tapped cards.
                args.append(1)
            card = getCard(args, field)
            if isinstance(card, Card):
                prev = None
                while card.tapped() and prev != card:
                    prev = card
                    args[-1] += 1
                    card = getCard(args, field)
            untap(card)
        else:
            raise CommandError

#------------------------------------------------------------------------------
# View
#
#         Syntax: view <card>
#-------#
        # The view command lets a user look at an image of a card
        # Enclosing the card name in double quotes will fetch the
        # exact card, otherwise the first card in the deck 
        # containing the given string will be printed.
        #----------------------------------------------------------------------
    if cmd == "view":
        if args:
            view(args)
            return False
        else:
            raise CommandError

#------------------------------------------------------------------------------
# Quit
#
#         Syntax: quit
#-------#
        # Command to exit the program
        #----------------------------------------------------------------------
    if cmd == "quit":
        sys.exit(0)
    
    # Return true to print the board state
    return True

#------------------------------------------------------------------------------
# Do executes cmd n times with args as its arguments.
# Do will iterate over multiple cards for things like tap and untap. Otherwise
# it will only act on a single card. Do attempts to iterate over cards for any
# command that does not move a card between zones. This means any command where
# the syntax <command> <card> <n> is valid and more meaningful that just
# <command> <card> would be. You do not need to specify n when running these.
# Commands where this is valid syntax but that move cards between zones,
# like "move" or "exile" will not. These commands will always act on the first
# card found, moving it out of the list it's in. Then it will again act on the
# first card, which is now different than before, so it behaves the same way.
#------------------------------------------------------------------------------
def do(cmd, args, n):
    iterate = ("counters", "power", "toughness", "plusone")
    if cmd in iterate:
        args.append(0)
    for i in range(0, n):
        if cmd in iterate:
            # The +1 gets cut off later
            args[-1] = i+1
        # Copy the args so that the command doesn't screw it 
        # up for the next iteration. Pretty much only happens
        # with tap and untap.
        copy = args[:]
        command(cmd, copy)

###############################################################################
#                                                                             #
#                               ACTUAL PROGRAM                                #
#                                                                             #
###############################################################################

#------------------------------------------------------------------------------
# Start of the program
#------------------------------------------------------------------------------

if len(sys.argv) == 2:
    load(sys.argv[1])
elif len(sys.argv) == 3 and sys.argv[1] == "debug":
    debug = True
    load(sys.argv[2])
else:
    print "Expected decklist file"
    sys.exit(1)

reset()

# This loop will accept and handle user input, using the functions
# defined above. Commands are expected in lowercase, but arguments
# are not case sensitive. Any card name may be followed by a
# positive integer n to perform the action on the nth card that
# action could legally be performed on.
while 1:
    # Check if anyone has won yet
    checkVictory()
    try:
        input = raw_input(">>").rstrip().lower()
        args = input.split(" ")
        cmd = args[0]
        if len(args) >= 2:
            args = args[1:]
        else:
            args = None
        
        # Only allow running of reset, quit, and view when the game is over
        if not GAME_OVER or cmd == "reset" or cmd == "quit" or cmd == "view":
            # Run the command
            state = command(cmd, args)
            # If we ran a command that needs to update the boardstate, do it
            if state:
                applyAnthems()
                stateBased()
                boardstate()
        else:
            print "Game finished."
    except CardNotFoundError as err:
        print "Failed to find \"" + err.args[0] + "\"."
    except ZoneError as err:
        print err.args[0]
    except CommandError:
        print "Invalid syntax for " + cmd
    #except Exception as err:
    #    print err

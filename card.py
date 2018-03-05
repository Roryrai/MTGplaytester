import re
import sys
import copy

# Python class to represent a magic card. This class stores relevant
# information like name, mana cost, type, etc. Also overrides the 
# __str__ function to allow for printing a card to the screen.
class Card:

    # Zone names
    BATTLEFIELD = "Battlefield"
    HAND = "Hand"
    LIBRARY = "Library"
    GRAVEYARD = "Graveyard"
    EXILE = "Exile"
    TOP = "Top"
    BOTTOM = "Bottom"
    COMMAND = "Command"
    
    # List in case iteration is needed
    ZONES = (BATTLEFIELD, COMMAND, EXILE, GRAVEYARD, HAND, LIBRARY, TOP, BOTTOM)
    
    # Type names
    ARTIFACT = "Artifact"
    CREATURE = "Creature"
    ENCHANTMENT = "Enchantment"
    EMBLEM = "Emblem"
    INSTANT = "Instant"
    LAND = "Land"
    PLANESWALKER = "Planeswalker"
    SNOW = "Snow"
    SORCERY = "Sorcery"
    TOKEN = "Token"
    TRIBAL = "Tribal"
    
    # List to iterate over them
    TYPES = (CREATURE, PLANESWALKER, ENCHANTMENT, ARTIFACT, LAND, INSTANT, SORCERY, TOKEN, EMBLEM)

    # Supertypes
    BASIC = "Basic"
    SNOW = "Snow"
    LEGENDARY = "Legendary"
    
    # List
    SUPERTYPES = (LEGENDARY, SNOW, BASIC)
    
    # Keywords
    FIRSTSTRIKE = "First strike"
    DOUBLESTRIKE = "Double strike"
    LIFELINK = "Lifelink"
    VIGILANCE = "Vigilance"
    FLYING = "Flying"
    DEATHTOUCH = "Deathtouch"
    HASTE = "Haste"
    TRAMPLE = "Trample"
    HEXPROOF = "Hexproof"
    SHROUD = "Shroud"
    PERSIST = "Persist"
    UNDYING = "Undying"
    FLASH = "Flash"
    FORESTWALK = "Forestwalk"
    ISLANDWALK = "Islandwalk"
    MOUNTAINWALK = "Mountainwalk"
    PLAINSWALK = "Plainswalk"
    SWAMPWALK = "Swampwalk"
    NONBASICLANDWALK = "Nonbasic landwalk"
    WITHER = "Wither"
    INFECT = "Infect"
    MORPH = "Morph"
    MEGAMORPH = "Megamorph"
    INDESTRUCTIBLE = "Indestructible"
    SKULK = "Skulk"
    DEFENDER = "Defender"
    MENACE = "Menace"
    PROWESS = "Prowess"
    REACH = "Reach"
    CHANGELING = "Changeling"
    SHADOW = "Shadow"
    
    
    # List
    KEYWORDS = (CHANGELING, DEATHTOUCH, DEFENDER, DOUBLESTRIKE, FIRSTSTRIKE, FLASH, FLYING, FORESTWALK, HASTE, HEXPROOF, INDESTRUCTIBLE, INFECT, ISLANDWALK, LIFELINK, MEGAMORPH, MENACE, MORPH, MOUNTAINWALK, PERSIST, PLAINSWALK, PROWESS, REACH, SKULK, SHADOW, SHROUD, SWAMPWALK, TRAMPLE, UNDYING, VIGILANCE, WITHER)
    
    
    # Regex to check the mana cost against
    costPattern = re.compile("^X?[1-9]?[0-9]*[WUBRGC]*$")
    # Width of th card, for printing
    # 36 for Windows
    width = 36
    # Height of the card, for printing
    # 28 for Windows
    height = 28
    
    #-----------------------------------------------------------------------------------------
    # Creates a new card with all relevant information. Raises a TypeError if power/toughness
    # and counters are not integers, and also if cost doesn't match the format for mana costs.
    #-----------------------------------------------------------------------------------------
    def __init__(self, name, cost, type, subtype, power, toughness, text, transform):
        self.__name = name
        if self.costPattern.match(cost) or cost == "TRANSFORM":
            self.__cost = cost
        else:
            raise TypeError("Mana cost for " + name + " is formatted incorrectly.")
        
        # Color related things
        self.__color = ""
        if "W" in self.__cost:
            self.__color += "White "
        if "U" in self.__cost:
            self.__color += "Blue "
        if "B" in self.__cost:
            self.__color += "Black "
        if "R" in self.__cost:
            self.__color += "Red "
        if "G" in self.__cost:
            self.__color += "Green "
        if self.__color == "":
            self.__color = "Colorless"
        self.__color = self.__color.rstrip()
        
        # Type and subtype
        self.__type = type
        self.__subtype = subtype
        
        # Power, toughness, and counters
        self.__powerMod = 0
        self.__toughnessMod = 0
        self.__countersMod = 0
        self.__counters = 0
        self.__plusone = 0
        self.__summoningSickness = False
        if Card.CREATURE in self.__type:
            self.__power = int(power)
            self.__toughness = int(toughness)
            self.__summoningSickness = True
        if type == Card.PLANESWALKER:
            self.__counters = int(power)
            
        # Numbers for an anthem provided by this card
        self.__hasAnthem = False
        self.__anthemPower = 0
        self.__anthemToughness = 0
        self.__anthemType = list()
        self.__anthemKeywords = list()
        
        # Bonuses this card gets from other anthems
        self.__anthemPowerBonus = 0
        self.__anthemToughnessBonus = 0
        self.__anthemKeywordMod = list()
        
        # Rules text
        self.__text = text.replace("\\", "\n")
        
        # Commander
        self.__commander = False
        
        # Flip and split card stuff
        self.__flip = False
        self.__split = False
        self.__linked = False
        
        # Zone the card is in
        self.__zone = Card.LIBRARY
        # Is the card tapped?
        self.__tapped = False
        # Is the card transformed?
        self.__transformed = False
        if transform:
            # Name of the back side of the card.
            # Replaced with the actual card later.
            self.__backSide = transform
        else:
            self.__backSide = None
        
        self.__keywords = list()
        self.__keywordMods = list()
        self.__parseText()
        
        self.__facedown = False
        self.__morph = False
        if Card.MORPH in self.__keywords or Card.MEGAMORPH in self.__keywords:
            self.__morph = True
            self.__morphToken()
        
    #--------------------------------------------------------------------------
    # Parses this card's rules text and determines what it needs to be able to
    # do. This includes:
    #    - Anthems
    #    - Keywords
    #--------------------------------------------------------------------------
    def __parseText(self):
        # Check for any keywords this card has. Not keywords it gives to other
        # things, just keywords that apply to this particular card.
        things = list()
        lines = self.__text.split("\n")
        validLine = True
        for line in lines:
            words = line.split(",")
            for word in words:
                if word.startswith(" "):
                    word = word[1:]
                word = word.rstrip().capitalize()
                if word in Card.KEYWORDS:
                    things.append(word)
                else:
                    validLine = False
            if validLine:
                for keyword in things:
                    self.__keywords.append(keyword)
        
        # Check for morph cards, since that's a keyword that doesn't get found
        # in the above keyword search because it also has a mana cost with it.
        morphPattern = re.compile("Morph|Megamorph X?[1-9]?[0-9]*[WUBRGC]*")
        match = morphPattern.search(self.__text)
        if match:
            words = match.group(0).split(" ")
            if words[0] == Card.MORPH:
                self.__keywords.append(Card.MORPH)
            elif words[0] == Card.MEGAMORPH:
                self.__keywords.append(Card.MEGAMORPH)
            else:
                # Wat
                pass
        
        # Check for anthems, not just limited to power/toughness bonuses
        # This will also allow things like "Creatures you control have flying"
        # to be applied and viewed in the playtester.
        
        # Regex has the form "(Other) <things> (, <more things>, and <more things>)
        # (you control) get +P/+T <other things>." where anything in parentheses is
        # considered optional. The minimum pattern to match is therefore
        # "<Things> get +P/+T."
        anthemPattern = re.compile("(Other )?[\w]*s?(,? (and )?[\w]*s?)* (you control)? get [+-][1-9]{1}[0-9]*/[+-][1-9]{1}[0-9]*.*\.")
        # While the previous pattern hits anthems with power and toughness in them
        # this one will hit things that only provide effects. This is the same regex but
        # without the power and toughness parts. This is only tested if the other one fails.
        keywordOnlyPattern = re.compile("(Other )?[\w]*s?(,? (and )?[\w]*s?)* (you control)? have .*\.")
        match = anthemPattern.search(self.__text)
        if not match:
            # Check that we don't have an anthem without power and toughness
            match = keywordOnlyPattern.search(self.__text)
        # If we got something, handle it
        if match:
            textString = match.group(0)
            if "until end of turn" in textString:
                # No anthem, just an end of turn modifier
                pass
            elif "\"" + textString + "\"" in self.__text:
                # The anthem will be on a different card. Probably a token or emblem or something.
                pass
            else:
                # We have an anthem on this card
                self.__hasAnthem = True
                words = textString.split(" ")
                # Sometimes this might happen?
                if "" in words:
                    words.remove("")
                # Some anthems only affect other cards, not themselves as well.
                if words[0] == "Other":
                    self.__anthemType.append("Other")
                    words.remove("Other")
                # Now look through the words we have and pull out all the types.
                # KNOWN BUG: This will NOT find types with more than one word.
                # For example, "Attacking creatures you control have double strike"
                # would return both "Attacking" and "Creature" as affected types.
                # This would later, in turn, attempt to give double strike to all
                # attackings, and also to all creatures, resulting in all creatures
                # having double strike permanently.
                for word in words:
                    # Things after these words aren't part of
                    # what the anthem affects
                    if word == "you" or word == "get":
                        break
                    # This means there are multiple types this affects
                    elif word == "and":
                        continue
                    else:
                        # Get rid of leading spaces since that can happen apparently
                        if word.startswith(" "):
                            word = word[1:]
                        # If there are multiple types affected this might exist, remove it
                        if word.endswith(","):
                            word = word[:-1]
                        # Get rid of plurals. It's an anthem, it hits everything.
                        if word.endswith("s"):
                            word = word[:-1]
                        # Just in case. Stranger things have happened.
                        word = word.rstrip().capitalize()
                        # We should be okay now so add the type to the list
                        self.__anthemType.append(word)
                # Regex to match power and toughness of the anthem.
                # Pretty much (read: actually) copied from above.
                ptPattern = re.compile("[+-][1-9]{1}[0-9]*/[+-][1-9]{1}[0-9]*")
                for word in words:
                    # Match power and toughness bonus
                    ptMatch = ptPattern.match(word)
                    # This will just fail on noncreature anthems or anthems with no bonus
                    if ptMatch:
                        ptString = ptMatch.group(0)
                        split = ptString.split("/")
                        self.__anthemPower = int(split[0])
                        self.__anthemToughness = int(split[1])
                        break
                # Now check the entire string for any and all keywords it contains.
                # Add them to the list.
                for keyword in Card.KEYWORDS:
                    #text = " ".join(words)
                    # Don't want to search the whole rulestext string, just
                    # search the anthem string. Searching all rulestext is bad.
                    if keyword.lower() in textString:
                        self.__anthemKeywords.append(keyword)
                
    ###########################################################################
    #                                                                         #
    #                 FUNCTIONS TO GET PROPERTIES OF THE CARD                 #
    #                                                                         #
    ###########################################################################
    
    #--------------------------------------------------------------------------
    # Return true if this card provides an anthem
    #--------------------------------------------------------------------------
    def anthem(self):
        if self.__transformed or self.__facedown:
            return self.__backSide.__hasAnthem
        return self.__hasAnthem

    #--------------------------------------------------------------------------
    # Returns the keywords provided by this card's anthem if it has one
    #--------------------------------------------------------------------------
    def anthemKeywords(self):
        if self.anthem():
            if self.__transformed or self.__facedown:
                return self.__backSide.__anthemKeywords
        return self.__anthemKeywords
    
    #--------------------------------------------------------------------------
    # Returns the power of this card's anthem if it has one
    #--------------------------------------------------------------------------
    def anthemPower(self):
        if self.anthem():
            if self.__transformed or self.__facedown:
                return self.__backSide.__anthemPower
            return self.__anthemPower
        return None
    
    #--------------------------------------------------------------------------
    # Returns the toughness of this card's anthem if it has one
    #--------------------------------------------------------------------------
    def anthemToughness(self):
        if self.anthem():
            if self.__transformed or self.__facedown:
                return self.__backSide.__anthemToughness
            return self.__anthemToughness
        return None
    
    #--------------------------------------------------------------------------
    # Returns the type of this card anthem if it has one
    #--------------------------------------------------------------------------
    def anthemType(self):
        if self.anthem():
            if self.__transformed or self.__facedown:
                return self.__backSide.__anthemType
            return self.__anthemType
        return None
    
    #--------------------------------------------------------------------------
    # Return the card CMC
    #--------------------------------------------------------------------------
    def cmc(self):
        cmc = 0
        for char in self.__cost:
            try:
                cmc += int(char)
            except TypeError:
                if char != "X":
                    cmc += 1
                continue
        return cmc
        
    #--------------------------------------------------------------------------
    # Return the card color
    #--------------------------------------------------------------------------
    def color(self):
        if self.__transformed or self.__facedown:
            return self.__backSide.__color
        return self.__color
    
    #--------------------------------------------------------------------------
    # Returns true if this card is a commander
    #--------------------------------------------------------------------------
    def commander(self):
        return self.__commander
    
    #--------------------------------------------------------------------------
    # Return the card cost
    #--------------------------------------------------------------------------
    def cost(self):
        return self.__cost
    
    #--------------------------------------------------------------------------
    # Return the number of counters on the card
    #--------------------------------------------------------------------------
    def counters(self):
        if self.__transformed or self.__facedown:
            return self.__backSide.__counters + self.__countersMod + abs(self.__plusone)
        return self.__counters + self.__countersMod + abs(self.__plusone)

    #--------------------------------------------------------------------------
    # Returns true if this card if face down.
    #--------------------------------------------------------------------------
    def facedown(self):
        return self.__facedown
    
    #--------------------------------------------------------------------------
    # Return the number of counters on the card
    #--------------------------------------------------------------------------
    def keywords(self):
        return self.__keywords + self.__anthemKeywordMod + self.__keywordMods
        
    #--------------------------------------------------------------------------
    # Return the card name
    #--------------------------------------------------------------------------
    def name(self):
        if self.__transformed or self.__facedown:
            return self.__backSide.__name
        return self.__name

    #--------------------------------------------------------------------------
    # Return the number of +1/+1 counters on the card
    # if it's a creature
    #--------------------------------------------------------------------------
    def plusone(self):
        if Card.CREATURE in self.__type:
            return self.__plusone
    
    #--------------------------------------------------------------------------
    # Return power, if the card is a creature
    #--------------------------------------------------------------------------
    def power(self):
        if Card.CREATURE in self.__type:
            if self.__transformed or self.__facedown:
                val = self.__backSide.__power + self.__powerMod + self.__anthemPowerBonus + self.__plusone
            else:
                val = self.__power + self.__powerMod + self.__anthemPowerBonus + self.__plusone
            if val < 0:
                return 0
            else:
                return val
    
    #--------------------------------------------------------------------------
    # Return the rulestext of the card
    #--------------------------------------------------------------------------
    def rulestext(self):
        if self.__transformed or self.__facedown:
            return self.__backSide.__text
        return self.__text
    
    #--------------------------------------------------------------------------
    # Return the card subtype
    #--------------------------------------------------------------------------
    def subtype(self):
        if self.__transformed or self.__facedown:
            return self.__backSide.__subtype
        return self.__subtype
    
    #--------------------------------------------------------------------------
    # Tells whether this card has summoning sickness or not.
    #--------------------------------------------------------------------------
    def summonSick(self):
        if Card.CREATURE in self.__type:
            return self.__summoningSickness
        else:
            return False
    
    #--------------------------------------------------------------------------
    # Returns true if this card is tapped
    #--------------------------------------------------------------------------
    def tapped(self):
        return self.__tapped
        
    #--------------------------------------------------------------------------
    # Return toughness, if the card is a creature
    #--------------------------------------------------------------------------
    def toughness(self):
        if Card.CREATURE in self.__type:
            if self.__transformed or self.__facedown:
                val = self.__backSide.__toughness + self.__toughnessMod + self.__anthemToughnessBonus + self.__plusone
            else:
                val = self.__toughness + self.__toughnessMod + self.__anthemToughnessBonus + self.__plusone
            if val < 0:
                return 0
            else:
                return val
    
    #--------------------------------------------------------------------------
    # Return the card type
    #--------------------------------------------------------------------------
    def type(self):
        if self.__transformed or self.__facedown:
            return self.__backSide.__type
        return self.__type
    
    #--------------------------------------------------------------------------
    # Return the zone the card is in
    #--------------------------------------------------------------------------
    def zone(self):
        return self.__zone
        

    ###########################################################################
    #                                                                         #
    #               FUNCTIONS TO MODIFY PROPERTIES OF THE CARD                #
    #                                                                         #
    ###########################################################################
    
    #--------------------------------------------------------------------------
    # Remove a counter from this card
    #--------------------------------------------------------------------------
    def anthemPowerBonus(self, n):
        self.__anthemPowerBonus += n

    #--------------------------------------------------------------------------
    # Remove a counter from this card
    #--------------------------------------------------------------------------
    def anthemToughnessBonus(self, n):
        self.__anthemToughnessBonus += n

    #--------------------------------------------------------------------------
    # Adds a keyword provided by an anthem to this card
    #--------------------------------------------------------------------------
    def anthemKeywordMod(self, keywords):
        self.__anthemKeywordMod += keywords
        
    #--------------------------------------------------------------------------
    # Remove a counter from this card
    #--------------------------------------------------------------------------
    def modCounters(self, n):
        if self.__zone == Card.BATTLEFIELD:
            self.__countersMod += n
            # Can't have less than 0
            if self.__counters + self.__countersMod < 0:
                self.__countersMod = 0 - self.__counters
    
    #------------------------------------------------------------------------------
    # Adds a keyword to a this card temporarily.
    #------------------------------------------------------------------------------
    def modKeywords(self, keyword):
        if keyword in Card.KEYWORDS and keyword != Card.MORPH and keyword != Card.MEGAMORPH:
            if keyword not in self.keywords():
                self.__keywordMods.append(keyword)
                if keyword == Card.HASTE:
                    self.__summoningSickness = False
                if keyword == Card.MORPH or keyword == Card.MEGAMORPH:
                    self.__morph = True
                    self.__morphToken()
        
    #--------------------------------------------------------------------------
    # Modify +1/+1 counters.
    #--------------------------------------------------------------------------
    def modPlusOne(self, n):
        if Card.CREATURE in self.__type and self.__zone == Card.BATTLEFIELD:
            self.__plusone += n
    
    #--------------------------------------------------------------------------
    # Modifies the power of a creature
    #--------------------------------------------------------------------------
    def modPower(self, n):
        if Card.CREATURE in self.__type and self.__zone == Card.BATTLEFIELD:
            self.__powerMod += n
    
    #--------------------------------------------------------------------------
    # Modifies the toughness of a creature.
    #--------------------------------------------------------------------------
    def modToughness(self, n):
        if Card.CREATURE in self.__type and self.__zone == Card.BATTLEFIELD:
            self.__toughnessMod += n
    
    #--------------------------------------------------------------------------
    # Resets anthem bonuses
    #--------------------------------------------------------------------------
    def resetAnthem(self):
        self.__anthemPowerBonus = 0
        self.__anthemToughnessBonus = 0
        del self.__anthemKeywordMod[:]

    #--------------------------------------------------------------------------
    # Set a card's color
    #--------------------------------------------------------------------------
    def setColor(self, newColor):
        pass
        
    #--------------------------------------------------------------------------
    # This card is a commander and should behave like one
    #--------------------------------------------------------------------------
    def setCommander(self):
        self.__commander = True
        self.__zone = Card.COMMAND
    
    #--------------------------------------------------------------------------
    # Set a card's subtype
    #--------------------------------------------------------------------------
    def setSubtype(self, newSubtype):
        self.__subtype = str(newSubtype)
        
    #--------------------------------------------------------------------------
    # Set a card's type
    #--------------------------------------------------------------------------
    def setType(self, newType):
        self.__type = str(newType)
    
    ###########################################################################
    #                                                                         #
    #                    FUNCTIONS TO MANIPULATE THE CARD                     #
    #                                                                         #
    ###########################################################################

    #--------------------------------------------------------------------------
    # Play this card. Automatically move it to the correct zone,
    # and cause any necessary effects to happen (ETBs and such)
    #--------------------------------------------------------------------------
    def play(self):
        if Card.INSTANT in self.__type or Card.SORCERY in self.__type:
            if "Exile " + self.__name in self.__text:
                self.__zone = Card.EXILE
            else:                
                self.__zone = Card.GRAVEYARD
        elif Card.ARTIFACT in self.__type or Card.CREATURE in self.__type or Card.ENCHANTMENT in self.__type or Card.LAND in self.__type:
            self.__zone = Card.BATTLEFIELD
            self.enter()
        elif Card.PLANESWALKER in self.__type:
            self.__zone = Card.BATTLEFIELD
            self.enter()
    
    #--------------------------------------------------------------------------
    # Tells the card to move to the next turn, resolving upkeep triggers?
    #--------------------------------------------------------------------------
    def nextTurn(self):
        if Card.CREATURE in self.__type:
            self.__summoningSickness = False
        
    #--------------------------------------------------------------------------
    # Ends the turn, removing "until end of turn" modifications to power and
    # toughness. This is handled by removing any changes that aren't +1/+1 or
    # -1/-1 counters.
    #--------------------------------------------------------------------------
    def endTurn(self):
        self.__powerMod = 0
        self.__toughnessMod = 0
        del self.__keywordMods[:]
        
    #--------------------------------------------------------------------------
    # Taps this card
    #--------------------------------------------------------------------------
    def tap(self):
        if self.__zone == Card.BATTLEFIELD:
            self.__tapped = True
        
    #--------------------------------------------------------------------------
    # Untaps this card
    #--------------------------------------------------------------------------
    def untap(self):
        self.__tapped = False
    
    #--------------------------------------------------------------------------
    # Discard this card, sending it to your graveyard
    #--------------------------------------------------------------------------
    def discard(self):
        if self.__zone == Card.HAND:
            self.__zone = Card.GRAVEYARD
            
    #--------------------------------------------------------------------------
    # Draw this card
    #--------------------------------------------------------------------------
    def draw(self):
        if self.__zone == Card.LIBRARY:
            self.__zone = Card.HAND
        else:
            raise ZoneError(Card.Hand)
            
    #--------------------------------------------------------------------------
    # This card entered the battlefield
    #--------------------------------------------------------------------------
    def enter(self):
        if self.__name + " enters the battlefield tapped" in self.__text:
            self.__tapped = True
        if self.__type == Card.CREATURE:
            if Card.HASTE in self.__keywords:
                self.__summoningSickness = False
        if "When " + self.__name + " enters the battlefield" in self.__text:
            #resolveTrigger()
            pass
        if self.__name + " enters the battlefield with "in self.__text:
            pass
    
    #--------------------------------------------------------------------------
    # This card left the battlefield
    #--------------------------------------------------------------------------
    def leave(self):
        if self.__transformed or self.__facedown:
            self.transform()
        self.__powerMod = 0
        self.__toughnessMod = 0
        self.__countersMod = 0
        self.__tapped = False
        if Card.CREATURE in self.__type and Card.HASTE not in self.__keywords:
            self.__summoningSickness = True
        
    #--------------------------------------------------------------------------
    # Morphs this card.
    #--------------------------------------------------------------------------
    def morph(self):
        if self.__morph:
            self.__facedown = not self.__facedown
    
    #--------------------------------------------------------------------------
    # Moves this card to the specified zone
    #--------------------------------------------------------------------------
    def move(self, zone):
        # Is this card leaving the battlefield?
        leaves = False
        if self.__zone == Card.BATTLEFIELD and zone != Card.BATTLEFIELD:
            leaves = True
        
        # Commanders are special
        if self.__commander:
            if zone != Card.HAND and zone != Card.BATTLEFIELD:
                self.__zone = Card.COMMAND
            else:
                self.__zone = zone
        # So are emblems
        elif Card.EMBLEM in self.__type:
            if zone != Card.BATTLEFIELD:
                raise ZoneError("Can't interact with emblems on the battlefield.")
            self.__zone = Card.BATTLEFIELD
        else:
            if zone != Card.COMMAND:
                self.__zone = zone
            else:
                raise ZoneError("Only the commander can be put in the command zone.")
        if leaves:
            self.leave()
    
    #--------------------------------------------------------------------------
    # Transform this card if it can
    #--------------------------------------------------------------------------
    def transform(self):
        if self.__flip:
            self.__transformed = not self.__transformed
        
    ###########################################################################
    #                                                                         #
    #                        DEALING WITH DOUBLE CARDS                        #
    #                                                                         #
    ###########################################################################

    #--------------------------------------------------------------------------
    # Returns true if this card is a spilt card
    #--------------------------------------------------------------------------
    def isSplit(self):
        return self.__split
    
    #--------------------------------------------------------------------------
    # Returns true if this card is a transform card
    #--------------------------------------------------------------------------
    def isTransform(self):
        return self.__flip
    
    #--------------------------------------------------------------------------
    # Returns true if this card is facedown (for a morph card)
    #--------------------------------------------------------------------------
    def faceDown(self):
        return self.__facedown
    
    #--------------------------------------------------------------------------
    # This card is a split card
    #--------------------------------------------------------------------------
    def setSplit(self):
        self.__split = True
        
    #--------------------------------------------------------------------------
    # This card is a transform card, make it behave like one
    #--------------------------------------------------------------------------
    def setTransform(self):
        self.__flip = True
    
    #--------------------------------------------------------------------------
    # Returns true if this card is a transform card and is
    # linked to a back side and false if it is not linked.
    # If this card is not a transform card, return null
    #--------------------------------------------------------------------------
    def linked(self):
        if self.__flip or self.__split:
            return self.__linked
        else:
            return None
    
    #--------------------------------------------------------------------------
    # Links the front face of a transform card to the back face
    #--------------------------------------------------------------------------
    def linkBackSide(self, card):
        self.__backSide = card
        self.__linked = True 
        if self.__split:
            self.__name += "/" + self.__backSide.__name

            self.__backSide.__name == self.__name
            
    #--------------------------------------------------------------------------
    # Returns the back side of a transform card
    #--------------------------------------------------------------------------
    def backSide(self):
        return self.__backSide

    #--------------------------------------------------------------------------
    # Generates a morph token and attaches it to the back side of this card.
    # This does NOT set the transform value.
    #--------------------------------------------------------------------------
    def __morphToken(self):
        morph = Card("Morph", "", "Creature", "", 2, 2, "", None)
        self.linkBackSide(morph)
    
    ###########################################################################
    #                                                                         #
    #                       FUNCTIONS FOR PRINTING CARDS                      #
    #                                                                         #
    ###########################################################################
    
    #--------------------------------------------------------------------------
    # The textwrap function is bad and cutting off my lines early
    #--------------------------------------------------------------------------
    def wrapText(self, text):
        # Split specifically on a space, not any whitespace
        tokens = text.split(" ")
        # Final string that will get returned
        string = ""
        linelength = 0
        for word in tokens:
            # No newline and word doesn't go over
            if not "\n" in word and linelength + len(word) + 1 <= self.width:
                if linelength > 0:
                    string += " "
                    linelength += 1
                string += word
                linelength += len(word)
            # No newline but word does go over
            elif not "\n" in word and linelength + len(word) + 1 > self.width:
                string += "\n"
                string += word
                linelength = len(word)
            # Newline in word, word does not go over
            elif "\n" in word and linelength + len(word.rstrip()) + 1 <= self.width:
                if linelength > 0:
                    string += " "
                string += word
                string += "\n"
                linelength = 0
            # Newline in word, word goes over
            else:
                string += "\n"
                string += word
                string += "\n"
                linelength = 0
        return string.rstrip()
    
    #--------------------------------------------------------------------------
    # Returns a string which when printed will form an image of the card.
    # View at your own risk.
    #--------------------------------------------------------------------------
    def image(self):
        cardImage = ""
        # Write the top border
        cardImage += " "
        for i in range(0, self.width):
            cardImage += "-"
        cardImage += " \n"
        # Write the first line with name and cost
        cardImage += "|"
        namelen = len(self.__name)
        if self.__split:
            shortName = self.__name.split("//")[0]
            cardImage += shortName
            namelen = len(shortName)
        else:
            cardImage += self.__name
        for i in range (0, (self.width - namelen - len(self.__cost))):
            cardImage += " "
        cardImage += self.__cost
        cardImage += "|\n"
        cardImage += "|"
        for i in range(0, self.width):
            cardImage += "-"
        cardImage += "|\n"
        # Blank space for ART
        for i in range(2, self.height/2 - 2):
            cardImage += "|"
            for j in range(0, self.width):
                cardImage += " "
            cardImage += "|\n"
        # Top border of the center section
        cardImage += "|"
        for i in range (0, self.width):
            cardImage += "-"
        cardImage += "|\n"
        # Center section
        cardImage += "|"
        typeStr = self.__type
        if self.__subtype:
            typeStr += " - " + self.__subtype
        cardImage += typeStr
        for i in range(0, self.width - len(typeStr)):
            cardImage += " "
        cardImage += "|\n"
        # Bottom border of center section
        cardImage += "|"
        for i in range (0, self.width):
            cardImage += "-"
        cardImage += "|\n"
        # Prepare to print rulestext....this will be difficult
        # Wrap text to self.width chars but keep existing newlines
        wrap = self.wrapText(self.__text)
        lineCount = 0
        lines = wrap.split("\n")
        # Each line in the wrapped text needs to be inserted into the card
        # with the right amount of padding for the border to line up.
        for line in lines:
            cardImage += "|"
            cardImage += line
            for i in range(len(line), self.width):
                cardImage += " "
            cardImage += "|\n"
            lineCount += 1
        if Card.CREATURE in self.__type or Card.PLANESWALKER in self.__type:
            # Print the rest of the card up to the power/toughness
            # 2 is to leave 2 lines for power/toughness
            for i in range(self.height/2 + 1 + lineCount, self.height - 2):
                cardImage += "|"
                for j in range(0, self.width):
                    cardImage += " "
                cardImage += "|\n"
            # Handle creatues. They get a larger box, an extra number, and a /
            if Card.CREATURE in self.__type:
                # Print the power/toughness lines
                cardImage += "|"
                # Extra 3 for whitespace and for the /
                box = 3 + len(str(self.power())) + len(str(self.toughness()))
                for i in range(0, self.width-box):
                    cardImage += " "
                # Write the top border of the P/T box
                for i in range(0, box):
                    cardImage += "-"
                cardImage += "|\n"
                # Line with power/toughness on it
                cardImage += "|"
                for i in range(0, self.width-(box+1)):
                    cardImage += " "
                cardImage += "| "
                cardImage += str(self.power())
                cardImage += "/"
                cardImage += str(self.toughness())
                cardImage += " "
            # Handle planeswalkers, their box size is smaller and they just have one number
            if Card.PLANESWALKER in self.__type:
                # Print the lines with the box for counters
                cardImage += "|"
                # Extra 2 for whitespace
                box = 2 + len(str(self.__counters + self.__countersMod))
                for i in range(0, self.width-box):
                    cardImage += " "
                # Write the top border of the box
                for i in range(0, box):
                    cardImage += "-"
                cardImage += "|\n"
                # Line with counters on it
                cardImage += "|"
                for i in range(0, self.width-(box+1)):
                    cardImage += " "
                cardImage += "| "
                cardImage += str(self.__counters + self.__countersMod)
                cardImage += " "
            cardImage += "|\n"            
        else:
            # If not a creature or a planeswalker the last 2 lines are normal
            for i in range(self.height/2 + 1 + lineCount, self.height):
                cardImage += "|"
                for j in range(0, self.width):
                    cardImage += " "
                cardImage += "|\n"
        # Write the bottom border
        cardImage += " "
        for i in range(0, self.width):
            cardImage += "-"
        cardImage += " \n"
        return cardImage
    
    #--------------------------------------------------------------------------
    # Overwrites the print function to print a card.
    # Single-faced cards will just call the image function above.
    # Double faced cards will image both sides, then split each
    # image on newlines and build a new string that prints both
    # cards side by side, instead of vertically.
    #--------------------------------------------------------------------------
    def __str__(self):
        cardFront = self.image()
        if self.__flip or self.__split:
            cardBack = self.__backSide.image()
            frontTokens = cardFront.split("\n")
            backTokens = cardBack.split("\n")
            numLines = len(frontTokens)
            card = ""
            for i in range(0, numLines):
                card += frontTokens[i]
                card += " "
                card += backTokens[i]
                card += "\n"
            return card
        else:
            return cardFront

    #--------------------------------------------------------------------------
    # Overrides the equality operator so that we can consider two cards to be
    # the same if they have the same name. If the card is a token, check other
    # fields as well, like power, toughness, color, and rulestext. That way we
    # don't accidentally compare a 1/1 cat with vigilance and a 2/2 vanilla cat
    # as the same just because they're both called "Cat".
    #
    # So apparently this was actually breaking stuff because reasons
    #--------------------------------------------------------------------------
    """def __eq__(self, other):
        if isinstance(other, self.__class__):
            if Card.TOKEN in other.__type or Card.TOKEN in self.__type:
                # Tokens have a few special cases.
                if self.__name == other.__name:
                    # If the token is a creature we check power, toughness
                    # and text
                    if Card.CREATURE in self.__type \
                            and Card.CREATURE in other.__type \
                            and self.__power == other.__power \
                            and self.__toughness == other.__toughness \
                            and self.__text == other.__text:
                        return True
                    # If not just check text
                    return self.__text == other.__text
                else:
                    # If they don't have the same name they're immediately
                    # considered different
                    return False
            else:
                # Nontokens we can just compare name. No two different cards
                # have the same name.
                return self.__name == other.__name
        else:
            # In this case the second object isn't even a card...
            return False"""
    
    #--------------------------------------------------------------------------
    # Returns a token that's a copy of this card.
    #--------------------------------------------------------------------------
    def copy(self):        
        token = copy.deepcopy(self)
        if not Card.TOKEN in token.__type:
            type = ""
            typenames = self.__type.split(" ")
            for cardtype in typenames:
                if cardtype in Card.SUPERTYPES:
                    type += cardtype + " "
            if not Card.TOKEN in self.__type:
                type += Card.TOKEN + " "
            for cardtype in typenames:
                if not cardtype in Card.SUPERTYPES:
                    type += cardtype + " "
            token.__type = type.rstrip()
        return token
        
    ###########################################################################
    #                                                                         #
    #                              CUSTOM ERRORS                              #
    #                                                                         #
    ###########################################################################

#------------------------------------------------------------------------------
# ZoneError will be used for anything involving incorrect zones.
#------------------------------------------------------------------------------
class ZoneError(Exception):
    pass

#------------------------------------------------------------------------------
# CardNotFoundErrors get raised any time that a card is missing from the deck.
#------------------------------------------------------------------------------
class CardNotFoundError(Exception):
    pass

#------------------------------------------------------------------------------
# CommandErrors get raised when the user screws up a command.
#------------------------------------------------------------------------------
class CommandError(Exception):
    pass

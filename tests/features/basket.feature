Feature: Deciding for yourself what goes

  Sift proposes; it never decides, and it never refuses. Anything it judged goes
  in the basket on one click, including the things it argued hardest against — it
  is your disk, and a tool that says no is a tool you work around, usually with
  rm, which has no undo.

  What the verdict buys is that you can see what you picked. It travels into the
  basket and onto the receipt, the plan never *proposes* something irreplaceable,
  and emptying is still a separate act with a countdown you can cancel. Choosing
  is yours; the tool's job is to make sure you know what you chose.

  Background:
    Given a machine that looks like a developer's Mac
    And the machine has been surveyed

  Scenario: Ordinary things go in the basket and out to quarantine
    When I put "Sites/client-app/node_modules" in the basket
    And I empty the basket
    Then "Sites/client-app/node_modules" is gone from where it was
    And it is sitting in quarantine

  Scenario: Something irreplaceable goes in on the same one click
    When I put ".ssh" in the basket
    Then the basket says ".ssh" cannot be replaced
    When I empty the basket
    Then ".ssh" is gone from where it was
    And it is sitting in quarantine

  Scenario: The receipt says what each thing was judged to be
    When I put ".ssh" in the basket
    And I empty the basket
    Then the receipt records ".ssh" as irreplaceable

  Scenario: Reclaiming something irreplaceable is as reversible as anything else
    When I put ".ssh" in the basket
    And I empty the basket
    And I undo
    Then ".ssh" is back where it was
    And it still holds everything it held before

  Scenario: A file inside an irreplaceable folder carries that verdict too
    When I put ".ssh/id_ed25519" in the basket
    Then the basket says "id_ed25519" cannot be replaced

  Scenario: One item that cannot move does not strand the rest
    When I put "Sites/client-app/node_modules" in the basket
    And I put "Library/Caches" in the basket
    And something in the basket disappears before it is emptied
    And I empty the basket
    Then everything that could move did
    And the receipt says what could not

  Scenario: A basket of several goes in one go
    When I put "Sites/client-app/node_modules" in the basket
    And I put "Library/Caches" in the basket
    And I empty the basket
    Then quarantine holds 2 items
    And it reports freeing what the basket held

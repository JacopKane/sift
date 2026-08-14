Feature: Surveying a machine

  The scanner has to stay correct on a real machine — an active project, stale
  build output, package caches, a locked directory and a symlink all present at
  once. Each of those is easy in isolation; the bugs live where they meet.

  Background:
    Given a machine that looks like a developer's Mac

  Scenario: Every readable byte is accounted for, exactly once
    When I survey the machine
    Then the survey total matches every file that was written
    And every directory equals the sum of what is beneath it

  Scenario: The survey reaches the places space actually hides
    When I survey the machine
    Then the survey includes "Library/Developer/Xcode/DerivedData"
    And the survey includes "Sites/client-app/node_modules"
    And the survey includes "Sites/old-project/target"
    And the survey includes ".npm/_cacache"

  Scenario: A locked directory costs us that directory and nothing else
    When I survey the machine
    Then "Library/Application Support/locked" is marked unreadable
    And the survey includes "Downloads/installer.dmg"
    And the survey total matches every file that was written

  Scenario: A symlink does not inflate the total
    When I survey the machine
    Then "shortcut-to-app" is absent from the survey
    And the survey total matches every file that was written

  Scenario: Sizes reflect what files occupy on disk
    When I survey the machine
    Then every file occupies at least its own size on disk

  Scenario: Results arrive while the survey is still running
    When I survey the machine
    Then "Sites/client-app/node_modules" is reported before "Sites/client-app"
    And "Sites" is reported before the machine root
    And the machine root is reported last
    And the last report carries the whole tree

  Scenario: The survey records when each thing was last opened
    When I survey the machine
    Then every file says when it was last opened
    And a directory says when anything inside it was last opened

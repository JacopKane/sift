Feature: Recognising what a directory is

  Most of what fills a disk is the same handful of things: package caches, build
  output, and downloads. Those are knowable from the path and the files sitting
  next to it, so recognising them needs no model at all — it needs a catalog, and
  it costs nothing.

  A model is for what the catalog cannot name. Every directory the catalog
  settles is one the model never has to be asked about.

  Background:
    Given a machine that looks like a developer's Mac

  Scenario: Package directories are recognised wherever they appear
    When I survey the machine
    Then "Sites/client-app/node_modules" is regenerable
    And "Sites/client-app/node_modules" can be restored with "npm install"

  Scenario: A build directory is recognised by the file sitting next to it
    When I survey the machine
    Then "Sites/old-project/target" is regenerable
    And "Sites/old-project/target" can be restored with "cargo build"

  Scenario: A directory called target with no Cargo.toml beside it is not assumed to be build output
    Given a folder "Documents/target" holding 200 KB
    When I survey the machine
    Then "Documents/target" is not recognised

  Scenario: Fixed locations are recognised by their path
    When I survey the machine
    Then "Library/Developer/Xcode/DerivedData" is regenerable
    And "Library/Caches" is regenerable
    And ".npm/_cacache" is regenerable

  Scenario: Personal directories are protected by the catalog, not merely unrecognised
    When I survey the machine
    Then "Documents" is irreplaceable
    And "Documents" is never proposed for deletion

  Scenario: Nothing the catalog already settled is sent to the model
    When I survey the machine
    Then "Sites/client-app/node_modules" is not a candidate
    And "Library/Caches" is not a candidate
    And no candidate was recognised by the catalog

  Scenario: The model is asked about opaque directories, not about every directory
    When I survey the machine
    Then "Downloads" is a candidate
    And "Archive" is a candidate
    And candidates are offered largest first
    And no candidate is inside another candidate
    And the model is asked about fewer than 10 directories

  Scenario: A directory holding recognised things is descended into, not asked about
    When I survey the machine
    Then "Sites" is not a candidate
    And "Library" is not a candidate
    And "Sites/client-app/src" is a candidate

  Scenario: A file is never mistaken for the directory a rule names
    Given a file "Sites/another/Cargo.toml" of 1 KB
    And a file "Sites/another/target" of 300 KB
    When I survey the machine
    Then "Sites/another/target" is not recognised

  Scenario: A candidate carries enough context for the model to reason about it
    When I survey the machine
    Then the candidate "Downloads" reports its largest files
    And the candidate "Downloads" reports which extensions fill it

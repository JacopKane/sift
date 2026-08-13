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
    Given a folder "Sites/notes/target" holding 200 KB
    When I survey the machine
    Then "Sites/notes/target" is not recognised

  Scenario: Fixed locations are recognised by their path
    When I survey the machine
    Then "Library/Developer/Xcode/DerivedData" is regenerable
    And "Library/Caches" is regenerable
    And ".npm/_cacache" is regenerable

  Scenario: Source next to its manifest is protected by rule, never by judgement
    When I survey the machine
    Then "Sites/client-app/src" is irreplaceable
    And "Sites/old-project/src" is irreplaceable
    And "Sites/client-app/src" is never proposed for deletion

  Scenario: Personal directories are protected by the catalog, not merely unrecognised
    When I survey the machine
    Then "Documents" is irreplaceable
    And "Documents" is never proposed for deletion

  Scenario: A recognised directory is counted without being explored
    When I survey the machine
    Then "Sites/client-app/node_modules" reports its full size
    And nothing inside "Sites/client-app/node_modules" was explored
    And "Library/Caches" reports its full size
    And nothing inside "Library/Caches" was explored

  Scenario: Nothing the catalog already settled is sent to the model
    When I survey the machine
    Then "Sites/client-app/node_modules" is not a candidate
    And "Library/Caches" is not a candidate
    And no candidate was recognised by the catalog

  Scenario: The model is asked about opaque directories, not about every directory
    When I survey the machine
    Then "Archive" is a candidate
    And "Sites/client-app/mockups" is a candidate
    And candidates are offered largest first
    And no candidate counts bytes another candidate already counted
    And the model is asked about fewer than 10 directories

  Scenario: A directory holding recognised things is descended into, not asked about
    When I survey the machine
    Then "Sites" is not a candidate
    And "Library" is not a candidate
    And "Sites/client-app/mockups" is a candidate

  Scenario: A file is never mistaken for the directory a rule names
    Given a file "Sites/another/Cargo.toml" of 1 KB
    And a file "Sites/another/target" of 300 KB
    When I survey the machine
    Then "Sites/another/target" is not recognised

  Scenario: A file big enough to decide on its own is judged on its own
    When I survey the machine
    Then "Downloads/screen-recording-2024-11-14.mp4" is a candidate
    And "Downloads/dataset-export.zip" is a candidate
    And "Downloads/invoice-2024-01.pdf" is not a candidate

  Scenario: What is left of a directory is still offered, without the files taken out of it
    When I survey the machine
    Then "Downloads" is a candidate
    And the candidate "Downloads" leaves out "screen-recording-2024-11-14.mp4"
    And the candidate "Downloads" reports its largest files
    And the candidate "Downloads" reports which extensions fill it

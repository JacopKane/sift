Feature: Choosing what to survey

  Sift has to work at both extremes — one project folder, or the whole boot
  volume — without changing how it is used.

  Surveying everything brings problems a project folder never has. Since APFS,
  macOS mounts the data volume at /System/Volumes/Data and firmlinks /Users and
  /Applications back into /, so a walk of / that also descends into
  /System/Volumes/Data counts the entire disk twice. /Volumes holds other disks
  entirely, and /dev holds device nodes that are not files at all.

  Background:
    Given a machine that looks like a developer's Mac

  Scenario: Surveying one project sees that project and nothing else
    When I survey "Sites/client-app"
    Then the survey includes "Sites/client-app/node_modules/react/index.js"
    And nothing outside "Sites/client-app" appears in the survey
    And the survey total is less than surveying the whole machine

  Scenario: An excluded directory is skipped entirely
    When I survey the machine excluding "Library"
    Then "Library" is absent from the survey
    And the survey total is less than surveying the whole machine
    And the survey includes "Sites/client-app/node_modules"

  Scenario: An excluded directory is never even opened
    When I survey the machine excluding "Library/Application Support/locked"
    Then "Library/Application Support/locked" is absent from the survey
    And the survey total matches every file that was written

  Scenario: Excluding something that is not there changes nothing
    When I survey the machine excluding "nowhere"
    Then the survey total matches every file that was written

  Scenario: A whole-volume survey skips the paths that would double-count
    When I ask what a boot volume survey excludes
    Then it excludes "/System/Volumes/Data"
    And it excludes "/Volumes"
    And it excludes "/dev"

Feature: Serving a survey to a browser

  A survey of a real disk takes long enough that holding everything back until it
  finishes would misrepresent what is happening. The browser is told about each
  directory as it is counted, and gets the plan when there is one.

  The scanner reports every file; the API forwards only directories. Deciding what
  is worth sending over a wire is a interface concern, and does not belong in a
  filesystem library.

  Background:
    Given a machine that looks like a developer's Mac

  Scenario: The browser is told about directories as they are counted
    When the browser surveys the machine
    Then it is told about "Sites/client-app/node_modules"
    And it is told about "Downloads"
    And it is never told about individual files

  Scenario: Each report carries the verdict the catalog reached
    When the browser surveys the machine
    Then the report for "Sites/client-app/node_modules" says regenerable
    And the report for "Sites/client-app/node_modules" says how to restore it

  Scenario: The map shows large files, not only directories
    When the browser surveys the machine
    Then the map includes "Downloads/screen-recording-2024-11-14.mp4"
    And the map leaves out files too small to see

  Scenario: The plan arrives once the survey is complete
    When the browser surveys the machine
    Then the survey finishes with a plan
    And the plan proposes reclaiming "node_modules"
    And the plan totals what is safe to reclaim

  Scenario: Reports arrive before the survey is finished
    When the browser surveys the machine
    Then directories are reported before the plan

  Scenario: The app serves a page
    When the browser opens the app
    Then it receives an HTML page
    And the page names the product

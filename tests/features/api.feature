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

  @slow
  Scenario: The map is coloured by what the model decided, not only by what the catalog knew
    When the browser surveys the machine and asks the model
    Then the map shows a verdict for "Downloads"
    And the map is not a single colour

  @slow
  Scenario: Colouring the map does not make the plan count anything twice
    When the browser surveys the machine and asks the model
    Then the plan the browser receives accounts for no more than was surveyed

  Scenario: The app serves a page
    When the browser opens the app
    Then it receives an HTML page
    And the page names the product

  Scenario: A survey that breaks says what broke
    Given a machine that looks like a developer's Mac
    When the survey is asked for a folder that is not there
    Then the stream says what went wrong in words
    And it does not blame the disk permissions

  Scenario: A survey outlives a model that will not answer
    Given a machine that looks like a developer's Mac
    And the model layer cannot answer
    When the browser surveys the machine and asks the model
    Then it still gets a plan for what the rules recognised
    And it is told the model could not be reached
    And it is not told the survey failed

  Scenario: The stream says enough to draw with while it is still counting
    Given a machine that looks like a developer's Mac
    When the browser surveys the machine
    Then each folder arrives with a name and a size
    And folders arrive well before the plan does

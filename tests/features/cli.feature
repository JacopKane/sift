Feature: Starting from the command line

  The window sift opens is the whole product, so what the command line says has
  to arrive there. Naming a folder means "survey this one"; naming nothing means
  "ask me".

  Scenario: Naming a folder surveys it on sight
    When sift is launched with a folder
    Then the window it opens is pointed at that folder

  Scenario: Naming nothing opens the picker
    When sift is launched with nothing
    Then the window it opens names no folder

  Scenario: The address it prints is one it is actually serving on
    Given something else is already holding the usual port
    When sift is launched with nothing
    Then it picks a port that is free
    And the window it opens points at that port

  Scenario: A port asked for by name is never quietly swapped
    Given something else is already holding the usual port
    When sift is launched asking for that exact port
    Then it stops and says the port is taken

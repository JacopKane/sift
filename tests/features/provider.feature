Feature: Choosing which model answers

  The provider is a setting, not a rewrite. Gemini, Claude and GPT are the same
  code path, and swapping between them is two environment variables.

  Nothing here calls a model. Which client gets built, and whether the key and
  the provider-specific options reach it, is knowable without spending anything —
  and it is the part that silently breaks when a provider is added.

  Scenario Outline: Each provider builds its own client
    Given the provider is "<provider>" using "<model>"
    When the chat model is built
    Then it is a <client>
    And it was given the key for that provider

    Examples:
      | provider     | model                 | client                |
      | google_genai | gemini-3.1-flash-lite | ChatGoogleGenerativeAI |
      | openai       | gpt-5-mini            | ChatOpenAI            |
      | anthropic    | claude-sonnet-5       | ChatAnthropic         |

  Scenario: Thinking is only switched off where that setting exists
    Given the provider is "google_genai" using "gemini-3.1-flash-lite"
    When the chat model is built
    Then thinking is disabled

  Scenario: A provider without a thinking budget is not handed one
    Given the provider is "openai" using "gpt-5-mini"
    When the chat model is built
    Then it was not handed a thinking budget

  Scenario: Every provider is paced by the same shared limiter
    Given the provider is "openai" using "gpt-5-mini"
    When the chat model is built
    Then it is paced by the shared limiter

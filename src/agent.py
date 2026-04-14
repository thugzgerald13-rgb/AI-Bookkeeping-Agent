import os
from langchain import LLMFactory, BookkeepingTools

def get_llm_provider(provider_name):
    """
    Returns the appropriate LLM provider based on provider_name.
    Supported providers: "OpenAI", "Anthropic", "Google".
    """    
    if provider_name == "OpenAI":
        return LLMFactory.create_openai()
    elif provider_name == "Anthropic":
        return LLMFactory.create_anthropic()
    elif provider_name == "Google":
        return LLMFactory.create_google()
    else:
        raise ValueError(f"Invalid provider: {provider_name}")

class ReactBookkeepingAgent:
    def __init__(self, provider_name):
        self.llm = get_llm_provider(provider_name)
        self.tools = BookkeepingTools()

    def process_transaction(self, transaction):
        self.tools.process(transaction)

    def categorize_expense(self, expense):
        return self.tools.categorize(expense)

    def generate_report(self, report_type):
        return self.tools.generate(report_type)

    def get_account_balance(self, account_id):
        return self.tools.get_balance(account_id)

    def create_ledger(self, entries):
        return self.tools.create_ledger(entries)

# Example usage:
if __name__ == '__main__':
    agent = ReactBookkeepingAgent(provider_name="OpenAI")
    # agent processes transactions, categorizes expenses, etc.

"""Customer support agent — dedicated A/B variant (config-bundle aware, IAM auth)."""
from strands import Agent, tool
from strands.models.bedrock import BedrockModel
from strands.hooks.events import BeforeModelCallEvent
from bedrock_agentcore.runtime import BedrockAgentCoreApp, BedrockAgentCoreContext

app = BedrockAgentCoreApp()
log = app.logger

MODEL_ID = "global.anthropic.claude-sonnet-4-6"
DEFAULT_SYSTEM_PROMPT = "You are a helpful and professional customer support assistant for an e-commerce company. Always use tools to get accurate information rather than guessing."

RETURN_POLICIES = {
    "electronics": {"window": "30 days", "condition": "Original packaging required, must be unused or defective", "refund": "Full refund to original payment method"},
    "accessories": {"window": "14 days", "condition": "Must be in original packaging, unused", "refund": "Store credit or exchange"},
    "audio": {"window": "30 days", "condition": "Defective items only after 15 days", "refund": "Full refund within 15 days, replacement after"},
}

PRODUCTS = {
    "PROD-001": {"name": "Wireless Headphones", "price": 79.99, "category": "audio", "description": "Noise-cancelling Bluetooth headphones with 30h battery life"},
    "PROD-002": {"name": "Smart Watch", "price": 249.99, "category": "electronics", "description": "Fitness tracker with heart rate monitor, GPS, and 5-day battery"},
    "PROD-003": {"name": "Laptop Stand", "price": 39.99, "category": "accessories", "description": "Adjustable aluminum laptop stand for ergonomic desk setup"},
    "PROD-004": {"name": "USB-C Hub", "price": 54.99, "category": "accessories", "description": "7-in-1 USB-C hub with HDMI, USB-A, SD card reader, and ethernet"},
    "PROD-005": {"name": "Mechanical Keyboard", "price": 129.99, "category": "electronics", "description": "RGB mechanical keyboard with Cherry MX switches"},
}

@tool
def get_return_policy(product_category: str) -> str:
    """Get return policy information for a specific product category (electronics, accessories, audio)."""
    policy = RETURN_POLICIES.get(product_category.lower())
    if policy:
        return f"Return policy for {product_category.lower()}: Window: {policy['window']}, Condition: {policy['condition']}, Refund: {policy['refund']}"
    return f"No specific return policy found for '{product_category}'. Please contact support."

@tool
def get_product_info(query: str) -> str:
    """Search for product information by name, ID (e.g. PROD-001), or keyword."""
    if query.upper() in PRODUCTS:
        p = PRODUCTS[query.upper()]
        return f"{p['name']} ({query.upper()}): ${p['price']}, Category: {p['category']}, {p['description']}"
    q = query.lower()
    results = [f"{pid}: {p['name']} - ${p['price']} - {p['description']}" for pid, p in PRODUCTS.items()
               if q in p['name'].lower() or q in p['description'].lower() or q in p['category'].lower()]
    return "Found products:\n" + "\n".join(results) if results else f"No products found matching '{query}'."

agent = Agent(
    model=BedrockModel(model_id=MODEL_ID),
    system_prompt=DEFAULT_SYSTEM_PROMPT,
    tools=[get_return_policy, get_product_info],
)

def dynamic_config_hook(event: BeforeModelCallEvent):
    """Apply the system prompt from the active config bundle before each model call."""
    try:
        config = BedrockAgentCoreContext.get_config_bundle()
    except Exception as e:
        log.warning(f"Could not read config bundle, using default prompt: {e}")
        config = {}
    event.agent.system_prompt = config.get("system_prompt", DEFAULT_SYSTEM_PROMPT)

agent.hooks.add_callback(BeforeModelCallEvent, dynamic_config_hook)


@app.entrypoint
def invoke(payload, context):
    result = agent(payload.get("prompt", "Hello"))
    return {"response": result.message["content"][0]["text"]}


if __name__ == "__main__":
    app.run()
TOPIC_GENERATION_PROMPT = """
Generate ONE LinkedIn post idea for a technical AI engineer.

The idea should:
- feel modern and relevant
- create curiosity
- trigger discussion
- sound like a real engineering observation
- avoid generic AI takes
- avoid motivational content
- avoid sounding corporate

Prioritize topics around:
- AI workflows
- agent systems
- context engineering
- developer leverage
- AI product design
- engineering tradeoffs
- AI-native software
- startup execution
- future of engineering

The idea should feel:
- sharp
- opinionated
- insightful
- naturally conversational

Avoid repetitive openings like:
- "I've been..."
- "I had a conversation..."
- "Recently..."
- "I noticed..."

Language rules:
- Write the topic idea in plain, everyday English
- Do not use buzzwords like "leverage", "paradigm", "synergy", "unlock",
  "game-changer", "disruptive", "revolutionize", "seamless", "robust",
  "cutting-edge", "next-generation", "groundbreaking", "transform"
- If a technical term is necessary, it must be something an engineer would
  actually say out loud — not marketing language

Return only the topic.
"""
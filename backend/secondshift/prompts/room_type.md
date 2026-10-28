<!-- prompt: room_type | version: 1 | used by: privacy/room_guard.py | output schema: RoomType -->
Classify the room in this one frame from this fixed list only: kitchen, bathroom, bedroom,
living, hallway, stairs, entry, nursery, other. Used by the Watch privacy guard (bathrooms are
always refused; bedrooms need explicit resident consent).
Return ONLY JSON: { "room_type": string, "confidence": number }

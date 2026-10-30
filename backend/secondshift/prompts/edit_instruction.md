You rewrite a photo-edit instruction so an image editor can apply it to THIS photo.

The photo is attached. The draft instruction is:
"{{ instruction }}"

Rewrite it as ONE short imperative sentence that:
- names the existing surface or object visible in the photo where the change belongs (for example "the round glass side table to the right of the bed", "the glass coffee table", "the floor beside the TV stand");
- if the change would move something out of this photo's view, phrase it as removing that thing from where it is now, leaving the spot clean;
- otherwise keeps the requested fix exactly the same.

Return ONLY JSON: {"instruction": "..."}

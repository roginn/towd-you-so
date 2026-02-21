import { useState } from "react";
import { Entry, UserMessageData } from "../types";

interface Props {
  entry: Entry;
}

export function MessageBubble({ entry }: Props) {
  const role = entry.kind === "user_message" ? "user" : "assistant";
  const data = entry.data as UserMessageData;
  const content = data.content;
  const imageUrl = entry.kind === "user_message" ? data.image_url : undefined;
  const [fullscreen, setFullscreen] = useState(false);

  return (
    <div className={`message ${role}`}>
      <div className="bubble">
        {imageUrl && (
          <>
            <img
              src={imageUrl}
              alt="Attached"
              className="bubble-image"
              onClick={() => setFullscreen(true)}
            />
            {fullscreen && (
              <div className="image-fullscreen" onClick={() => setFullscreen(false)}>
                <img src={imageUrl} alt="Attached full size" />
              </div>
            )}
          </>
        )}
        {content}
      </div>
    </div>
  );
}

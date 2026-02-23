import { Entry } from "./types";

const SESSION_ID = "s1";

export const MOCK_ENTRIES: Entry[] = [
  {
    id: "m1",
    sessionId: SESSION_ID,
    kind: "user_message",
    data: { content: "Can I park here until 6pm?", image_url: "parking_sign.jpg" },
    createdAt: "2026-02-21T14:32:00Z",
  },
  {
    id: "m2",
    sessionId: SESSION_ID,
    kind: "tool_call",
    data: {
      call_id: "tc1",
      tool_name: "read_parking_sign",
      arguments: { image_url: "parking_sign.jpg" },
    },
    createdAt: "2026-02-21T14:32:01Z",
  },
  {
    id: "m3",
    sessionId: SESSION_ID,
    kind: "tool_result",
    data: {
      call_id: "tc1",
      result:
        "Detected sign text:\n- NO PARKING 8AM-6PM MON-FRI\n- 2 HOUR PARKING 6PM-8AM MON-FRI\n- 2 HOUR PARKING SAT-SUN",
    },
    createdAt: "2026-02-21T14:32:03Z",
  },
  {
    id: "m4",
    sessionId: SESSION_ID,
    kind: "sub_agent_call",
    data: { call_id: "s2", agent_name: "sign_parser" },
    createdAt: "2026-02-21T14:32:04Z",
  },
  {
    id: "m5",
    sessionId: SESSION_ID,
    kind: "sub_agent_result",
    data: {
      call_id: "s2",
      result: {
        rules: [
          { days: "Mon-Fri", time: "8AM-6PM", action: "NO PARKING" },
          { days: "Mon-Fri", time: "6PM-8AM", action: "2 HOUR PARKING" },
          { days: "Sat-Sun", time: "all day", action: "2 HOUR PARKING" },
        ],
      },
    },
    createdAt: "2026-02-21T14:32:06Z",
  },
  {
    id: "m6",
    sessionId: SESSION_ID,
    kind: "reasoning",
    data: {
      content:
        "Current time: Saturday 2:32 PM. The sign says NO PARKING Mon-Fri 8AM-6PM, which does not apply today. On weekends, 2-hour parking is allowed all day. The user wants to park until 6pm — that's about 3.5 hours from now, which exceeds the 2-hour limit.",
    },
    createdAt: "2026-02-21T14:32:07Z",
  },
  {
    id: "m7",
    sessionId: SESSION_ID,
    kind: "assistant_message",
    data: {
      content:
        "**No, you probably shouldn't park here until 6pm.**\n\nToday is Saturday, so the weekday \"No Parking 8AM–6PM\" rule doesn't apply. However, weekend parking is limited to **2 hours**. Since it's currently 2:32 PM and you want to stay until 6 PM (~3.5 hours), you'd exceed the 2-hour limit.\n\nYou could park here until about **4:30 PM** to stay within the 2-hour window.",
    },
    createdAt: "2026-02-21T14:32:08Z",
  },
  {
    id: "m8",
    sessionId: SESSION_ID,
    kind: "user_message",
    data: { content: "What about tomorrow? I need to park from 7am to 10am." },
    createdAt: "2026-02-21T14:33:00Z",
  },
  {
    id: "m9",
    sessionId: SESSION_ID,
    kind: "reasoning",
    data: {
      content:
        "Tomorrow is Sunday, still a weekend. Weekend rule: 2-hour parking all day. The user wants 7 AM to 10 AM — that's 3 hours, still exceeds the 2-hour limit.",
    },
    createdAt: "2026-02-21T14:33:01Z",
  },
  {
    id: "m10",
    sessionId: SESSION_ID,
    kind: "assistant_message",
    data: {
      content:
        "**No — same issue.** Tomorrow is Sunday, so the weekend 2-hour parking limit applies. 7 AM to 10 AM is 3 hours, which exceeds the limit.\n\nYou'd need to move your car by **9 AM** to stay legal. Tow'd you so!",
    },
    createdAt: "2026-02-21T14:33:02Z",
  },
];

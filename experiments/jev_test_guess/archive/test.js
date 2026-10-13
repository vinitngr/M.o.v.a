export const sessions = [
  // ==========================================================
  // SESSION 01 — SOLO USER (TRIP PLANNING)
  // ==========================================================
  {
    id: "solo_trip",
    participants: [{ id: "U", role: "mute_user" }],
    scene: "The user is alone at home planning a trip to Jaipur.",
    turns: [
      { speaker: "U", mode: "gesture_interpretation", text: "tomorrow... train... Jaipur", quality: "fragmented" },
      { speaker: "U", mode: "gesture_interpretation", text: "need ticket", quality: "fragmented" }
    ],
    decisions: [
      {
        id: "solo_trip_01",
        category: "travel_planning",
        current_fragment: "train Jaipur",
        gesture: "QUESTION_TIME",
        candidates: ["when", "how_long", "frequency"],
        expected: "when"
      },
      {
        id: "solo_trip_02",
        category: "travel_planning",
        current_fragment: "need ticket",
        gesture: "QUESTION_LOCATION",
        candidates: ["where", "direction", "distance"],
        expected: "where"
      }
    ]
  },

  // ==========================================================
  // SESSION 02 — RAILWAY STATION
  // ==========================================================
  {
    id: "railway_station",
    participants: [
      { id: "U", role: "mute_user" },
      { id: "R", role: "friend" }
    ],
    scene: "The user and friend are at a busy railway station.",
    turns: [
      { speaker: "R", mode: "speech", text: "You said you wanted to meet your brother today. His train arrives this afternoon." },
      { speaker: "U", mode: "gesture_interpretation", text: "brother... meet... station", quality: "fragmented" },
      { speaker: "R", mode: "speech", text: "Yes, his train should arrive around four." },
      { speaker: "U", mode: "gesture_interpretation", text: "I go... platform", quality: "fragmented" },
      { speaker: "R", mode: "speech", text: "His train is arriving on platform four." }
    ],
    decisions: [
      {
        id: "railway_01",
        category: "transportation",
        current_fragment: "brother meet station",
        gesture: "QUESTION_LOCATION",
        candidates: ["where", "direction", "distance"],
        expected: "where"
      },
      {
        id: "railway_02",
        category: "transportation",
        current_fragment: "I go platform",
        gesture: "QUESTION_ENTITY",
        candidates: ["which", "who", "what"],
        expected: "which"
      },
      {
        id: "railway_03",
        category: "transportation",
        current_fragment: "brother train",
        gesture: "QUESTION_TIME",
        candidates: ["when", "duration", "frequency"],
        expected: "when"
      }
    ]
  },

  // ==========================================================
  // SESSION 03 — SHOPPING
  // ==========================================================
  {
    id: "shop",
    participants: [
      { id: "U", role: "mute_user" },
      { id: "S", role: "shopkeeper" }
    ],
    scene: "The user is inside a clothing shop.",
    turns: [
      { speaker: "U", mode: "gesture_interpretation", text: "shirt... blue... this", quality: "fragmented" },
      { speaker: "S", mode: "speech", text: "Yes, this blue shirt is available in another size." },
      { speaker: "U", mode: "gesture_interpretation", text: "another size", quality: "fragmented" },
      { speaker: "S", mode: "speech", text: "I have medium and large." }
    ],
    decisions: [
      {
        id: "shop_01",
        category: "shopping",
        current_fragment: "blue shirt this",
        gesture: "QUESTION_ENTITY",
        candidates: ["which", "who", "what"],
        expected: "which"
      },
      {
        id: "shop_02",
        category: "shopping",
        current_fragment: "another size",
        gesture: "QUESTION_ENTITY",
        candidates: ["which", "who", "what"],
        expected: "which"
      },
      {
        id: "shop_03",
        category: "shopping",
        current_fragment: "medium large",
        gesture: "QUESTION_ENTITY",
        candidates: ["which", "who", "what"],
        expected: "which"
      }
    ]
  },

  // ==========================================================
  // SESSION 04 — POLICE STATION / MISSING ITEM
  // ==========================================================
  {
    id: "police",
    participants: [
      { id: "U", role: "mute_user" },
      { id: "P", role: "police_officer" }
    ],
    scene: "The user is speaking with a police officer on a street about a lost phone.",
    turns: [
      { speaker: "U", mode: "gesture_interpretation", text: "phone... missing", quality: "fragmented" },
      { speaker: "P", mode: "speech", text: "When did you last have your phone?" },
      { speaker: "U", mode: "gesture_interpretation", text: "bus... maybe", quality: "uncertain" },
      { speaker: "P", mode: "speech", text: "Do you think you lost it on the bus?" },
      { speaker: "U", mode: "gesture_interpretation", text: "yes... bus", quality: "fragmented" }
    ],
    decisions: [
      {
        id: "police_01",
        category: "police_security",
        current_fragment: "phone missing",
        gesture: "QUESTION_LOCATION",
        candidates: ["where", "direction", "distance"],
        expected: "where"
      },
      {
        id: "police_02",
        category: "police_security",
        current_fragment: "bus maybe",
        gesture: "QUESTION_LOCATION",
        candidates: ["where", "direction", "distance"],
        expected: "where"
      },
      {
        id: "police_03",
        category: "police_security",
        current_fragment: "yes bus",
        gesture: "QUESTION_LOCATION",
        candidates: ["where", "direction", "distance"],
        expected: "where"
      }
    ]
  },

  // ==========================================================
  // SESSION 05 — HOSPITAL / MEDICAL
  // ==========================================================
  {
    id: "hospital",
    participants: [
      { id: "U", role: "mute_user" },
      { id: "D", role: "doctor" },
      { id: "F", role: "family_member" }
    ],
    scene: "The user is in a hospital room with a doctor and family member.",
    turns: [
      { speaker: "F", mode: "speech", text: "They have been having pain since yesterday evening." },
      { speaker: "D", mode: "speech", text: "Where exactly does it hurt?" },
      { speaker: "U", mode: "gesture_interpretation", text: "chest... little", quality: "fragmented" },
      { speaker: "D", mode: "speech", text: "Is the pain constant or does it come and go?" },
      { speaker: "U", mode: "gesture_interpretation", text: "come... go", quality: "fragmented" },
      { speaker: "F", mode: "speech", text: "They also felt dizzy this morning." }
    ],
    decisions: [
      {
        id: "hospital_01",
        category: "medical",
        current_fragment: "chest little",
        gesture: "QUESTION_LOCATION",
        candidates: ["where", "direction", "distance"],
        expected: "where"
      },
      {
        id: "hospital_02",
        category: "medical",
        current_fragment: "come go",
        gesture: "QUESTION_TIME",
        candidates: ["when", "duration", "frequency"],
        expected: "when"
      },
      {
        id: "hospital_03",
        category: "medical",
        current_fragment: "dizzy morning",
        gesture: "QUESTION_TIME",
        candidates: ["when", "duration", "frequency"],
        expected: "when"
      }
    ]
  },

  // ==========================================================
  // SESSION 06 — CLASSROOM / SCHOOL
  // ==========================================================
  {
    id: "classroom",
    participants: [
      { id: "U", role: "mute_student" },
      { id: "T", role: "teacher" },
      { id: "C", role: "classmate" }
    ],
    scene: "The user is in a classroom during a programming lesson.",
    turns: [
      { speaker: "T", mode: "speech", text: "The assignment is due tomorrow at five PM." },
      { speaker: "U", mode: "gesture_interpretation", text: "assignment... tomorrow", quality: "fragmented" },
      { speaker: "C", mode: "speech", text: "The submission is through the college portal." },
      { speaker: "U", mode: "gesture_interpretation", text: "portal... submit", quality: "fragmented" },
      { speaker: "T", mode: "speech", text: "Yes, upload the ZIP file there." }
    ],
    decisions: [
      {
        id: "class_01",
        category: "school",
        current_fragment: "assignment tomorrow",
        gesture: "QUESTION_TIME",
        candidates: ["when", "duration", "frequency"],
        expected: "when"
      },
      {
        id: "class_02",
        category: "school",
        current_fragment: "portal submit",
        gesture: "QUESTION_LOCATION",
        candidates: ["where", "direction", "distance"],
        expected: "where"
      },
      {
        id: "class_03",
        category: "school",
        current_fragment: "upload ZIP",
        gesture: "QUESTION_MANNER",
        candidates: ["how", "why", "purpose"],
        expected: "how"
      }
    ]
  },

  // ==========================================================
  // SESSION 07 — STREET EMERGENCY
  // ==========================================================
  {
    id: "street_emergency",
    participants: [
      { id: "U", role: "mute_user" },
      { id: "S", role: "stranger" },
      { id: "P", role: "police_officer" }
    ],
    scene: "The user is standing on a street after seeing a traffic accident.",
    turns: [
      { speaker: "U", mode: "gesture_interpretation", text: "accident... car", quality: "fragmented" },
      { speaker: "S", mode: "speech", text: "The ambulance has already been called." },
      { speaker: "U", mode: "gesture_interpretation", text: "person... injured", quality: "fragmented" },
      { speaker: "P", mode: "speech", text: "Is the injured person inside the car?" },
      { speaker: "U", mode: "gesture_interpretation", text: "car... person", quality: "uncertain" }
    ],
    decisions: [
      {
        id: "emergency_01",
        category: "emergencies",
        current_fragment: "accident car",
        gesture: "QUESTION_ENTITY",
        candidates: ["what", "who", "which"],
        expected: "what"
      },
      {
        id: "emergency_02",
        category: "emergencies",
        current_fragment: "person injured",
        gesture: "QUESTION_ENTITY",
        candidates: ["who", "what", "which"],
        expected: "who"
      },
      {
        id: "emergency_03",
        category: "emergencies",
        current_fragment: "car person",
        gesture: "QUESTION_LOCATION",
        candidates: ["where", "direction", "distance"],
        expected: "where"
      }
    ]
  },

  // ==========================================================
  // SESSION 08 — HOTEL / TRAVEL
  // ==========================================================
  {
    id: "hotel",
    participants: [
      { id: "U", role: "mute_user" },
      { id: "R", role: "receptionist" }
    ],
    scene: "The user is checking into a hotel.",
    turns: [
      { speaker: "U", mode: "gesture_interpretation", text: "reservation... Vinit", quality: "fragmented" },
      { speaker: "R", mode: "speech", text: "Yes, I found your reservation for two nights." },
      { speaker: "U", mode: "gesture_interpretation", text: "two nights... room", quality: "fragmented" },
      { speaker: "R", mode: "speech", text: "Your room is on the fourth floor." }
    ],
    decisions: [
      {
        id: "hotel_01",
        category: "workplace_travel",
        current_fragment: "reservation Vinit",
        gesture: "QUESTION_ENTITY",
        candidates: ["what", "who", "which"],
        expected: "what"
      },
      {
        id: "hotel_02",
        category: "workplace_travel",
        current_fragment: "two nights room",
        gesture: "QUESTION_ENTITY",
        candidates: ["which", "who", "what"],
        expected: "which"
      },
      {
        id: "hotel_03",
        category: "workplace_travel",
        current_fragment: "room fourth floor",
        gesture: "QUESTION_LOCATION",
        candidates: ["where", "direction", "distance"],
        expected: "where"
      }
    ]
  },

  // ==========================================================
  // SESSION 09 — SCENE-BASED ADJECTIVE COMPLIMENTS
  // ==========================================================
  {
    id: "descriptive_compliment",
    participants: [
      { id: "U", role: "mute_user" },
      { id: "O", role: "companion" }
    ],
    scene: "The user is looking at a male friend who just put on a new suit for an interview.",
    turns: [
      { speaker: "O", mode: "speech", text: "How do I look in this new blazer?" },
      { speaker: "U", mode: "gesture_interpretation", text: "you... suit... looking", quality: "fragmented" }
    ],
    decisions: [
      {
        id: "compliment_01",
        category: "adjective_compliment",
        current_fragment: "you suit looking",
        gesture: "COMPLIMENT",
        candidates: ["handsome", "beautiful", "delicious", "tasty"],
        expected: "handsome"
      }
    ]
  },

  {
    id: "descriptive_compliment_female",
    participants: [
      { id: "U", role: "mute_user" },
      { id: "O", role: "female_friend" }
    ],
    scene: "The user is talking to a female friend who is wearing an elegant wedding dress.",
    turns: [
      { speaker: "O", mode: "speech", text: "Does this dress look nice on me?" },
      { speaker: "U", mode: "gesture_interpretation", text: "dress... you... looking", quality: "fragmented" }
    ],
    decisions: [
      {
        id: "compliment_02",
        category: "adjective_compliment",
        current_fragment: "dress you looking",
        gesture: "COMPLIMENT",
        candidates: ["handsome", "beautiful", "delicious", "spicy"],
        expected: "beautiful"
      }
    ]
  },

  {
    id: "descriptive_compliment_food",
    participants: [
      { id: "U", role: "mute_user" },
      { id: "W", role: "waiter" }
    ],
    scene: "The user is eating a hot steamy dish at a restaurant.",
    turns: [
      { speaker: "W", mode: "speech", text: "How is the pasta tasting?" },
      { speaker: "U", mode: "gesture_interpretation", text: "pasta... food... tasting", quality: "fragmented" }
    ],
    decisions: [
      {
        id: "compliment_03",
        category: "adjective_compliment",
        current_fragment: "pasta food tasting",
        gesture: "COMPLIMENT",
        candidates: ["handsome", "beautiful", "delicious", "smart"],
        expected: "delicious"
      }
    ]
  },

  // ==========================================================
  // SESSION 10 — SCENE CONTEXT ASSISTANCE & DRINKS
  // ==========================================================
  {
    id: "need_assistance_medical",
    participants: [
      { id: "U", role: "mute_patient" },
      { id: "N", role: "nurse" }
    ],
    scene: "The user is lying in an emergency hospital room with high fever.",
    turns: [
      { speaker: "U", mode: "gesture_interpretation", text: "fever... high... call", quality: "fragmented" }
    ],
    decisions: [
      {
        id: "need_01",
        category: "medical_emergency",
        current_fragment: "fever high call",
        gesture: "NEED_HELP",
        candidates: ["doctor", "mechanic", "police", "waiter"],
        expected: "doctor"
      }
    ]
  },

  {
    id: "need_assistance_roadside",
    participants: [
      { id: "U", role: "mute_driver" },
      { id: "S", role: "passerby" }
    ],
    scene: "The user's car has broken down on a highway with smoke coming from engine.",
    turns: [
      { speaker: "U", mode: "gesture_interpretation", text: "car engine... broken... call", quality: "fragmented" }
    ],
    decisions: [
      {
        id: "need_02",
        category: "roadside_assistance",
        current_fragment: "car engine broken call",
        gesture: "NEED_HELP",
        candidates: ["doctor", "mechanic", "police", "waiter"],
        expected: "mechanic"
      }
    ]
  },

  {
    id: "drink_cold_weather",
    participants: [
      { id: "U", role: "mute_user" },
      { id: "H", role: "host" }
    ],
    scene: "The user is shivering indoors during a freezing winter snowfall.",
    turns: [
      { speaker: "H", mode: "speech", text: "You look so cold! What can I get you to drink?" },
      { speaker: "U", mode: "gesture_interpretation", text: "cold... drink... want", quality: "fragmented" }
    ],
    decisions: [
      {
        id: "drink_01",
        category: "daily_conversation",
        current_fragment: "cold drink want",
        gesture: "WANT_DRINK",
        candidates: ["hot_tea", "ice_water", "cold_soda", "lemonade"],
        expected: "hot_tea"
      }
    ]
  },

  {
    id: "drink_hot_weather",
    participants: [
      { id: "U", role: "mute_user" },
      { id: "H", role: "host" }
    ],
    scene: "The user is sweating heavily at a sunny beach on a 40°C afternoon.",
    turns: [
      { speaker: "H", mode: "speech", text: "It is extremely hot outside today!" },
      { speaker: "U", mode: "gesture_interpretation", text: "sweating... drink... want", quality: "fragmented" }
    ],
    decisions: [
      {
        id: "drink_02",
        category: "daily_conversation",
        current_fragment: "sweating drink want",
        gesture: "WANT_DRINK",
        candidates: ["hot_tea", "ice_water", "hot_coffee", "soup"],
        expected: "ice_water"
      }
    ]
  }
];

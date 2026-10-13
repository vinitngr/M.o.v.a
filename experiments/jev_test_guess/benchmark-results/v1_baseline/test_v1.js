export const sessions = [

  // ==========================================================
  // SESSION 01 — SOLO USER
  // One participant.
  // User is internally planning what they want to communicate.
  // ==========================================================

  {
    id: "solo_trip",

    participants: [
      { id: "U", role: "mute_user" }
    ],

    scene:
      "The user is alone at home planning a trip.",

    turns: [
      {
        speaker: "U",
        mode: "gesture_interpretation",
        text: "tomorrow... train... Jaipur",
        quality: "fragmented"
      },

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text: "need ticket",
        quality: "fragmented"
      }
    ],

    decisions: [

      {
        id: "solo_trip_01",

        current_fragment:
          "train Jaipur",

        gesture: "QUESTION",

        candidates: [
          "where",
          "when",
          "why",
          "how",
          "what"
        ],

        expected: "when"
      },

      {
        id: "solo_trip_02",

        current_fragment:
          "need ticket",

        gesture: "QUESTION",

        candidates: [
          "where",
          "when",
          "why",
          "how",
          "what"
        ],

        expected: "where"
      }
    ]
  },


  // ==========================================================
  // SESSION 02 — USER + FRIEND
  // Friend has already established important context.
  // ==========================================================

  {
    id: "railway_station",

    participants: [
      { id: "U", role: "mute_user" },
      { id: "R", role: "friend" }
    ],

    scene:
      "The user and friend are at a busy railway station.",

    turns: [

      {
        speaker: "R",
        mode: "speech",
        text:
          "You said you wanted to meet your brother today. His train arrives this afternoon."
      },

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "brother... meet... station",
        quality: "fragmented"
      },

      {
        speaker: "R",
        mode: "speech",
        text:
          "Yes, his train should arrive around four."
      },

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "I go... platform",
        quality: "fragmented"
      },

      {
        speaker: "R",
        mode: "speech",
        text:
          "His train is arriving on platform four."
      }
    ],

    decisions: [

      {
        id: "railway_01",

        current_fragment:
          "brother... meet... station",

        gesture: "QUESTION",

        candidates: [
          "where",
          "when",
          "who",
          "why",
          "how"
        ],

        expected: "where"
      },

      {
        id: "railway_02",

        current_fragment:
          "I go... platform",

        gesture: "QUESTION",

        candidates: [
          "which",
          "where",
          "when",
          "why",
          "how"
        ],

        expected: "which"
      },

      {
        id: "railway_03",

        current_fragment:
          "brother train",

        gesture: "QUESTION",

        candidates: [
          "when",
          "where",
          "who",
          "why",
          "how"
        ],

        expected: "when"
      }
    ]
  },


  // ==========================================================
  // SESSION 03 — USER + SHOPKEEPER
  // Previous conversation establishes what "it" refers to.
  // ==========================================================

  {
    id: "shop",

    participants: [
      { id: "U", role: "mute_user" },
      { id: "S", role: "shopkeeper" }
    ],

    scene:
      "The user is inside a clothing shop.",

    turns: [

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "shirt... blue... this",
        quality: "fragmented"
      },

      {
        speaker: "S",
        mode: "speech",
        text:
          "Yes, this blue shirt is available in another size."
      },

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "another size",
        quality: "fragmented"
      },

      {
        speaker: "S",
        mode: "speech",
        text:
          "I have medium and large."
      }
    ],

    decisions: [

      {
        id: "shop_01",

        current_fragment:
          "blue shirt this",

        gesture: "QUESTION",

        candidates: [
          "which",
          "what",
          "where",
          "how",
          "why"
        ],

        expected: "which"
      },

      {
        id: "shop_02",

        current_fragment:
          "another size",

        gesture: "QUESTION",

        candidates: [
          "which",
          "what",
          "where",
          "how",
          "why"
        ],

        expected: "which"
      },

      {
        id: "shop_03",

        current_fragment:
          "medium large",

        gesture: "QUESTION",

        candidates: [
          "which",
          "where",
          "when",
          "why",
          "how"
        ],

        expected: "which"
      }
    ]
  },


  // ==========================================================
  // SESSION 04 — USER + POLICE OFFICER
  // Multiple possible interpretations.
  // Earlier turns establish the missing object/person.
  // ==========================================================

  {
    id: "police",

    participants: [
      { id: "U", role: "mute_user" },
      { id: "P", role: "police_officer" }
    ],

    scene:
      "The user is speaking with a police officer on a street.",

    turns: [

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "phone... missing",
        quality: "fragmented"
      },

      {
        speaker: "P",
        mode: "speech",
        text:
          "When did you last have your phone?"
      },

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "bus... maybe",
        quality: "uncertain"
      },

      {
        speaker: "P",
        mode: "speech",
        text:
          "Do you think you lost it on the bus?"
      },

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "yes... bus",
        quality: "fragmented"
      }
    ],

    decisions: [

      {
        id: "police_01",

        current_fragment:
          "phone missing",

        gesture: "QUESTION",

        candidates: [
          "where",
          "when",
          "who",
          "why",
          "how"
        ],

        expected: "where"
      },

      {
        id: "police_02",

        current_fragment:
          "bus maybe",

        gesture: "QUESTION",

        candidates: [
          "where",
          "when",
          "why",
          "who",
          "how"
        ],

        expected: "where"
      },

      {
        id: "police_03",

        current_fragment:
          "yes bus",

        gesture: "QUESTION",

        candidates: [
          "where",
          "when",
          "why",
          "how",
          "what"
        ],

        expected: "where"
      }
    ]
  },


  // ==========================================================
  // SESSION 05 — USER + DOCTOR + FAMILY MEMBER
  // Three participants.
  // Speaker identity matters.
  // ==========================================================

  {
    id: "hospital",

    participants: [
      { id: "U", role: "mute_user" },
      { id: "D", role: "doctor" },
      { id: "F", role: "family_member" }
    ],

    scene:
      "The user is in a hospital room with a doctor and family member.",

    turns: [

      {
        speaker: "F",
        mode: "speech",
        text:
          "They have been having pain since yesterday evening."
      },

      {
        speaker: "D",
        mode: "speech",
        text:
          "Where exactly does it hurt?"
      },

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "chest... little",
        quality: "fragmented"
      },

      {
        speaker: "D",
        mode: "speech",
        text:
          "Is the pain constant or does it come and go?"
      },

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "come... go",
        quality: "fragmented"
      },

      {
        speaker: "F",
        mode: "speech",
        text:
          "They also felt dizzy this morning."
      }
    ],

    decisions: [

      {
        id: "hospital_01",

        current_fragment:
          "chest little",

        gesture: "QUESTION",

        candidates: [
          "where",
          "when",
          "why",
          "how",
          "what"
        ],

        expected: "where"
      },

      {
        id: "hospital_02",

        current_fragment:
          "come go",

        gesture: "QUESTION",

        candidates: [
          "when",
          "how",
          "why",
          "where",
          "what"
        ],

        expected: "when"
      },

      {
        id: "hospital_03",

        current_fragment:
          "dizzy morning",

        gesture: "QUESTION",

        candidates: [
          "when",
          "why",
          "where",
          "how",
          "what"
        ],

        expected: "when"
      }
    ]
  },


  // ==========================================================
  // SESSION 06 — CLASSROOM
  // Three participants.
  // Earlier speech changes meaning of later gesture.
  // ==========================================================

  {
    id: "classroom",

    participants: [
      { id: "U", role: "mute_student" },
      { id: "T", role: "teacher" },
      { id: "C", role: "classmate" }
    ],

    scene:
      "The user is in a classroom during a programming lesson.",

    turns: [

      {
        speaker: "T",
        mode: "speech",
        text:
          "The assignment is due tomorrow at five PM."
      },

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "assignment... tomorrow",
        quality: "fragmented"
      },

      {
        speaker: "C",
        mode: "speech",
        text:
          "The submission is through the college portal."
      },

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "portal... submit",
        quality: "fragmented"
      },

      {
        speaker: "T",
        mode: "speech",
        text:
          "Yes, upload the ZIP file there."
      }
    ],

    decisions: [

      {
        id: "class_01",

        current_fragment:
          "assignment tomorrow",

        gesture: "QUESTION",

        candidates: [
          "when",
          "where",
          "what",
          "why",
          "how"
        ],

        expected: "when"
      },

      {
        id: "class_02",

        current_fragment:
          "portal submit",

        gesture: "QUESTION",

        candidates: [
          "where",
          "how",
          "when",
          "what",
          "why"
        ],

        expected: "where"
      },

      {
        id: "class_03",

        current_fragment:
          "upload ZIP",

        gesture: "QUESTION",

        candidates: [
          "how",
          "where",
          "when",
          "what",
          "why"
        ],

        expected: "how"
      }
    ]
  },


  // ==========================================================
  // SESSION 07 — FRIEND GROUP
  // Four participants.
  // This tests whether speaker identity and prior discussion
  // are retained rather than just using the latest sentence.
  // ==========================================================

  {
    id: "friends",

    participants: [
      { id: "U", role: "mute_user" },
      { id: "A", role: "friend" },
      { id: "B", role: "friend" },
      { id: "C", role: "friend" }
    ],

    scene:
      "Four friends are discussing dinner plans at a cafe.",

    turns: [

      {
        speaker: "A",
        mode: "speech",
        text:
          "I can drive everyone to the restaurant."
      },

      {
        speaker: "B",
        mode: "speech",
        text:
          "I want to try the new place near the mall."
      },

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "new place... dinner",
        quality: "fragmented"
      },

      {
        speaker: "C",
        mode: "speech",
        text:
          "They have both vegetarian and non-vegetarian food."
      },

      {
        speaker: "A",
        mode: "speech",
        text:
          "We can leave at eight."
      },

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "leave eight",
        quality: "fragmented"
      }
    ],

    decisions: [

      {
        id: "friends_01",

        current_fragment:
          "new place dinner",

        gesture: "QUESTION",

        candidates: [
          "where",
          "what",
          "when",
          "which",
          "why"
        ],

        expected: "where"
      },

      {
        id: "friends_02",

        current_fragment:
          "leave eight",

        gesture: "QUESTION",

        candidates: [
          "when",
          "where",
          "why",
          "how",
          "who"
        ],

        expected: "when"
      }
    ]
  },


  // ==========================================================
  // SESSION 08 — STREET EMERGENCY
  // Two other people.
  // Scene is important.
  // ==========================================================

  {
    id: "street_emergency",

    participants: [
      { id: "U", role: "mute_user" },
      { id: "S", role: "stranger" },
      { id: "P", role: "police_officer" }
    ],

    scene:
      "The user is standing on a street after seeing a traffic accident.",

    turns: [

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "accident... car",
          quality: "fragmented"
      },

      {
        speaker: "S",
        mode: "speech",
        text:
          "The ambulance has already been called."
      },

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "person... injured",
          quality: "fragmented"
      },

      {
        speaker: "P",
        mode: "speech",
        text:
          "Is the injured person inside the car?"
      },

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "car... person",
          quality: "uncertain"
      }
    ],

    decisions: [

      {
        id: "emergency_01",

        current_fragment:
          "accident car",

        gesture: "QUESTION",

        candidates: [
          "where",
          "what",
          "when",
          "who",
          "how"
        ],

        expected: "what"
      },

      {
        id: "emergency_02",

        current_fragment:
          "person injured",

        gesture: "QUESTION",

        candidates: [
          "who",
          "where",
          "why",
          "when",
          "how"
        ],

        expected: "who"
      },

      {
        id: "emergency_03",

        current_fragment:
          "car person",

        gesture: "QUESTION",

        candidates: [
          "where",
          "who",
          "what",
          "why",
          "how"
        ],

        expected: "where"
      }
    ]
  },


  // ==========================================================
  // SESSION 09 — HOTEL / TRAVEL
  // Context must survive several turns.
  // ==========================================================

  {
    id: "hotel",

    participants: [
      { id: "U", role: "mute_user" },
      { id: "R", role: "receptionist" }
    ],

    scene:
      "The user is checking into a hotel.",

    turns: [

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "reservation... Vinit",
        quality: "fragmented"
      },

      {
        speaker: "R",
        mode: "speech",
        text:
          "Yes, I found your reservation for two nights."
      },

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "two nights... room",
        quality: "fragmented"
      },

      {
        speaker: "R",
        mode: "speech",
        text:
          "Your room is on the fourth floor."
      }
    ],

    decisions: [

      {
        id: "hotel_01",

        current_fragment:
          "reservation Vinit",

        gesture: "QUESTION",

        candidates: [
          "where",
          "when",
          "what",
          "who",
          "how"
        ],

        expected: "what"
      },

      {
        id: "hotel_02",

        current_fragment:
          "two nights room",

        gesture: "QUESTION",

        candidates: [
          "which",
          "where",
          "when",
          "how",
          "why"
        ],

        expected: "which"
      },

      {
        id: "hotel_03",

        current_fragment:
          "room fourth floor",

        gesture: "QUESTION",

        candidates: [
          "where",
          "when",
          "which",
          "why",
          "how"
        ],

        expected: "where"
      }
    ]
  },


  // ==========================================================
  // SESSION 10 — IMPORTANT: PREVIOUS CONTEXT IS MISLEADING
  //
  // The current conversation changes direction.
  // This tests whether Jev gives enough weight to RECENT
  // context rather than blindly following old context.
  // ==========================================================

  {
    id: "context_shift",

    participants: [
      { id: "U", role: "mute_user" },
      { id: "F", role: "friend" }
    ],

    scene:
      "Two friends are walking through a shopping area.",

    turns: [

      {
        speaker: "F",
        mode: "speech",
        text:
          "Yesterday you were asking where the new cafe was."
      },

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "yes cafe",
          quality: "fragmented"
      },

      {
        speaker: "F",
        mode: "speech",
        text:
          "We already went there yesterday. Today we need to buy your medicine."
      },

      {
        speaker: "U",
        mode: "gesture_interpretation",
        text:
          "medicine... pharmacy",
          quality: "fragmented"
      },

      {
        speaker: "F",
        mode: "speech",
        text:
          "The pharmacy is closed. There is another one two streets away."
      }
    ],

    decisions: [

      {
        id: "shift_01",

        current_fragment:
          "yes cafe",

        gesture: "QUESTION",

        candidates: [
          "where",
          "when",
          "why",
          "what",
          "how"
        ],

        expected: "where"
      },

      {
        id: "shift_02",

        current_fragment:
          "medicine pharmacy",

        gesture: "QUESTION",

        candidates: [
          "where",
          "when",
          "why",
          "which",
          "how"
        ],

        expected: "where"
      },

      {
        id: "shift_03",

        current_fragment:
          "another one two streets",

        gesture: "QUESTION",

        candidates: [
          "where",
          "which",
          "when",
          "why",
          "how"
        ],

        expected: "where"
      }
    ]
  },

  // ==========================================================
  // SESSION 11 — SCENE DISAMBIGUATION (COMPLIMENT / GOOD SIGN)
  // Testing user's scenario: GOOD_SIGN / COMPLIMENT gesture
  // mapped to adjective choices (handsome, beautiful, delicious, etc.)
  // based strictly on male vs female vs food scene context.
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
  // SESSION 12 — NEED ASSISTANCE (SCENE CONTEXT)
  // Gesture: NEED_HELP
  // Context determines whether helper is doctor, mechanic, or cashier.
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

  // ==========================================================
  // SESSION 13 — DRINK PREFERENCE (ENVIRONMENT SCENE)
  // Scene environment determines whether hot tea or cold water is intended.
  // ==========================================================

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
  },

  // ==========================================================
  // SESSION 14 — SUB-GESTURE QUESTIONS (SPECIFIC QUESTION GESTURES)
  // Testing specific question sub-gestures (QUESTION_LOCATION vs QUESTION_TIME)
  // ==========================================================

  {
    id: "sub_gesture_tests",
    participants: [
      { id: "U", role: "mute_user" },
      { id: "F", role: "friend" }
    ],
    scene: "Two friends planning to meet at the library.",
    turns: [
      { speaker: "F", mode: "speech", text: "Let us meet for studying." },
      { speaker: "U", mode: "gesture_interpretation", text: "library... study", quality: "fragmented" }
    ],
    decisions: [
      {
        id: "sub_01",
        category: "sub_gesture_location",
        current_fragment: "library study",
        gesture: "QUESTION_LOCATION",
        candidates: ["where", "which_floor", "near_gate"],
        expected: "where"
      },
      {
        id: "sub_02",
        category: "sub_gesture_time",
        current_fragment: "library study",
        gesture: "QUESTION_TIME",
        candidates: ["when", "what_time", "how_long"],
        expected: "when"
      }
    ]
  }
];



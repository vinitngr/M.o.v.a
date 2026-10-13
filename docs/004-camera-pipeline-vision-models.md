                         CAMERA
                            │
                            ▼
                    ┌──────────────┐
                    │ Frame stream │
                    └──────┬───────┘
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
         MediaPipe       YOLO         SmolVLM
          30 FPS         10-20 FPS      2-5 FPS
             │             │             │
             │             │             │
             ▼             ▼             ▼
        Hand/body       Objects       Scene/action
         geometry       + boxes        context
             │             │             │
             └─────────────┼─────────────┘
                           ▼
                    VISUAL STATE
                           │
                           ▼
                         JEV
                           │
                  + conversation
                  + current gesture
                  + visual state
                           │
                           ▼
                    semantic intent

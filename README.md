# time management

mvp ready by 25.10.2025 (night) -> add nice-to-have features + presentation 26.10.2025 by 14:00 

# tech stack used

- lovable
- react 
- fastapi
- python
- openai
  - agents builder
  - gpt-5
- weaviate

# project idea

tacto track -> supplier sourcing automation

# side challenges 

think later (after mvp built)

# requirements

## must-have

- buyer input form
- matching & ranking (top 3)
- conversation automation
- results email to buyer
- investigation similarity

## nice-to-have

todo: add after must-haves

# end-to-end flow

1. user input
2. input translated into vector  
3. vector similarity check in database
4. similarity score check
    - if similarity score is high -> return investigation result
    - if similarity score is low-med -> start a new investigation
5. api call to Exa with user input
6. parse top3 results with email provided (full name & email)
7. conversation loop with those 3 PoCs start
    - send a template reachout message (for now hardcoded)
    - parse replies
    - respond accordingly
    - repeat
8. identify if the email is the actual PoC
9. send results (maybe logs) to buyer email

# responsibilities

* Muslim - 1-4 tasks in end-to-end flow
* Moritz, Leandro, David - 5-9 tasks in the end-to-end flow

I want to create a plugin that will manage my skills. I already have a skill creator skill created. It's just the base one from Anthropic with an improvement to add a metadata reference.
Example workflows:

- User wants to install/create a new skill with the given keywords or instructions; 
  The agent asks clarifying questions or requests more information if necessary;
  The agent then proceeds to search for existing skills using the skill finder skill that we will create; 
  It will present the findings in a native multi-choice display, letting the user choose the skills they find interesting;
  If the user chooses more than zero skills, the skills will be cloned and go through a deep analysis. 
  Then, if the user didn't choose any skill, it will present the user with the option to create a new skill and ask for the name of the skill;
  Then agent creates a prompt using the prompt expert skill/plugin from the keywords or from the user's explanation (The prompt expert is not managed by this plugin);
  If the user chooses one option from the list, the agent will proceed by letting the user know the results of the analysis and then by asking the user if they want to copy the skill as it is or create an improved skill using the skill creator and using the selected skill as a base and the name of the new skill;
  If the user chooses more than one option from the list, the agent will proceed by letting the user know the results of the analysis and then the agent will ask which should be used as a base, or create a new one using the skill creator and applying the improvements from the selected skill sand the name of the new skill;
  The last information should be if it's a local project skill or if it's a global skill;
  Then the agent proceeds by creating the skill;
  Then, it verifies the skill;
  After that, testing. 
  After that, compliance with the user's personal preferences. 

- User wants to fix an existing skill. 
- User wants to update an existing skill. 
- User wants to find a skill. 
- User wants to add a new feature to an existing skill. 
- User wants to improve an existing skill by getting features from other skills.

# The river took their land. Where did they go?

In 2010, a household head in rural Bangladesh reported moving from Faridpur District to Manikganj District after river erosion caused the loss of land or homestead land.

The survey keeps this person anonymous. We do not know their name, what they packed, who traveled with them, or how they weighed their options. We know where the household started, where it arrived, when the move happened, and the reason recorded in the interview.

Those four facts let us ask a question that climate-migration research often leaves unanswered: after environmental damage pushes or helps set a move in motion, why does a household arrive in one place rather than another?

Researchers usually study the place people leave. They measure floods, erosion, crop loss, and the probability of migration. This project follows the move to its destination.

For each observed move, we gave a statistical model the same choice faced on paper: all 64 districts in Bangladesh. One model used two pieces of information. It knew how far each district was from the origin and how many people lived there. This is a gravity model. Nearby, populous places receive more weight.

A second model kept distance and population, then added four mapped features of every candidate district:

- the share of land that had experienced flooding in a global satellite archive;
- the share covered by buildings;
- estimated travel time to a city of at least 50,000 people;
- the share classified as cropland.

For the Faridpur household, the gravity model gave Manikganj a 7.0% probability and ranked it sixth among the 64 districts. The GIS model raised that probability to 13.7% and moved Manikganj to second place.

The model did not read the household's mind. It still ranked Faridpur first, so it did not reproduce the move perfectly. It made the place the household chose much more plausible.

One household can illustrate the problem, but it cannot establish the result. We tested the same model in two independent surveys.

The Bangladesh Environmental Mobility Panel followed communities exposed to riverbank erosion and flooding along the Jamuna River. Among 184 household moves preceded by a recorded flood or erosion shock, the GIS model assigned more probability to the destinations people chose than the gravity model did. The average log-loss gain was 0.108, with an uncertainty interval from 0.023 to 0.189.

The Bangladesh Integrated Household Survey gave us an independent check. Among 123 household moves explicitly attributed to erosion-related land loss, the gain was 0.098, with an interval from 0.028 to 0.163. A much larger sample of 1,857 current migrants produced a gain of 0.108.

The repetition across surveys is the strongest part of the evidence. The samples were collected by different projects and define migration differently. We did not choose new GIS variables after seeing the second survey's outcome. The same four destination features improved the held-out predictions again.

We then made the test harder. The model had to predict movers from an origin district it had never seen during training. The national migration sample passed that test. The smaller climate-related samples exposed a limit. They did not reliably predict whether a household would remain inside its origin district when that origin was absent from training. Once a cross-district move was known to have occurred, the destination advantage remained positive, though the small samples produced wide uncertainty.

This split tells us where the next research belongs. The choice to rebuild nearby may depend on details that district maps miss: available land, relatives, rent, credit, relief, roads, and whether a house can be dismantled before the river reaches it. The choice among farther destinations may carry more information from the receiving places themselves.

Social ties are an especially large missing piece. In the national survey, 1,815 of 1,857 current migrants said friends or family at the destination helped them. We left that field out of the model because the survey only records it after the person moved and only for the chosen destination. A fair destination model would need the same pre-move network measure for every district the household could have chosen.

The project does not prove that built-up land, cropland, accessibility, or flood history caused anyone to move. It does show that distance and population leave useful geographic information on the table.

The Faridpur household's record remains spare. The work cannot give the person back a name or recover the conversation that preceded the move. It can place their journey inside a national set of alternatives and show that Manikganj was more understandable once the destination itself came into view.

## Data and limits

The analysis uses public district identifiers from BEMP and BIHS, Bangladesh Bureau of Statistics population data, and global satellite products. Public survey files do not provide exact household locations. All models operate at district scale. Results describe prediction conditional on an observed move and should not be read as estimates of how environmental shocks change the probability of migration.

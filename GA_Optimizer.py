import random
from datetime import datetime, timedelta


class ExamPlannerGA:
    """
    Genetic Algorithm for optimizing a student's exam-season study schedule.

    The optimizer is completely independent from the UI.
    It receives structured data and returns structured results.

    Subject format:
    {
        "name": "Mathematics",
        "priority": 5,
        "hours_needed": 12,
        "exam_date": "2026-09-10"
    }

    Study slot format:
    {
        "start": "2026-09-01 09:00",
        "end": "2026-09-01 10:00"
    }
    """

    # ---------------------------------------------------------
    # INITIALIZATION
    # ---------------------------------------------------------

    def __init__(
        self,
        subjects,
        study_slots,
        population_size=30,
        generations=100,
        mutation_rate=0.10,
        elitism_count=1,
        random_seed=None
    ):
        """
        Parameters
        ----------
        subjects : list[dict]
            List of subjects to study.

        study_slots : list[dict]
            Available study slots.

        population_size : int
            Number of chromosomes in each generation.

        generations : int
            Number of generations.

        mutation_rate : float
            Probability of mutating each gene.

        elitism_count : int
            Number of best chromosomes preserved each generation.

        random_seed : int | None
            Optional seed for reproducible results.
        """

        if random_seed is not None:
            random.seed(random_seed)

        self.subjects = self._validate_subjects(subjects)
        self.study_slots = self._validate_study_slots(study_slots)

        self.population_size = max(2, population_size)
        self.generations = max(1, generations)
        self.mutation_rate = max(0.0, min(1.0, mutation_rate))

        self.elitism_count = max(
            1,
            min(elitism_count, self.population_size)
        )

        self.subject_count = len(self.subjects)
        self.slot_count = len(self.study_slots)

        self.best_scores = []
        self.average_scores = []
        self.worst_scores = []

    # ---------------------------------------------------------
    # VALIDATION
    # ---------------------------------------------------------

    def _validate_subjects(self, subjects):
        if not subjects:
            raise ValueError("At least one subject is required.")

        validated = []

        for index, subject in enumerate(subjects):
            required_fields = [
                "name",
                "priority",
                "hours_needed",
                "exam_date"
            ]

            for field in required_fields:
                if field not in subject:
                    raise ValueError(
                        f"Subject {index + 1} is missing '{field}'."
                    )

            name = str(subject["name"]).strip()

            if not name:
                raise ValueError(
                    f"Subject {index + 1} must have a name."
                )

            priority = int(subject["priority"])
            hours_needed = int(subject["hours_needed"])

            if not 1 <= priority <= 5:
                raise ValueError(
                    f"Priority for '{name}' must be between 1 and 5."
                )

            if hours_needed <= 0:
                raise ValueError(
                    f"Hours needed for '{name}' must be greater than 0."
                )

            exam_date = self._parse_datetime(
                subject["exam_date"],
                date_only=True
            )

            validated.append(
                {
                    "name": name,
                    "priority": priority,
                    "hours_needed": hours_needed,
                    "exam_date": exam_date
                }
            )

        return validated

    def _validate_study_slots(self, study_slots):
        if not study_slots:
            raise ValueError("At least one study slot is required.")

        validated = []

        for index, slot in enumerate(study_slots):
            if "start" not in slot:
                raise ValueError(
                    f"Study slot {index + 1} is missing 'start'."
                )

            start = self._parse_datetime(slot["start"])

            if "end" in slot:
                end = self._parse_datetime(slot["end"])
            else:
                end = start + timedelta(hours=1)

            if end <= start:
                raise ValueError(
                    f"Study slot {index + 1} has an invalid end time."
                )

            duration = (end - start).total_seconds() / 3600

            validated.append(
                {
                    "start": start,
                    "end": end,
                    "duration": duration
                }
            )

        validated.sort(key=lambda x: x["start"])

        return validated

    @staticmethod
    def _parse_datetime(value, date_only=False):
        if isinstance(value, datetime):
            return value

        value = str(value)

        formats = []

        if date_only:
            formats = [
                "%Y-%m-%d",
                "%d-%m-%Y",
                "%Y/%m/%d"
            ]
        else:
            formats = [
                "%Y-%m-%d %H:%M",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M",
                "%Y-%m-%dT%H:%M:%S"
            ]

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue

        raise ValueError(
            f"Invalid date/time format: '{value}'"
        )

    # ---------------------------------------------------------
    # CHROMOSOME
    # ---------------------------------------------------------

    def create_chromosome(self):
        """
        Each gene represents one study slot.

        Gene value = index of the subject assigned to that slot.

        Example:

        [0, 0, 2, 1, 0, 3]

        means:

        Slot 1 -> Subject 0
        Slot 2 -> Subject 0
        Slot 3 -> Subject 2
        Slot 4 -> Subject 1
        Slot 5 -> Subject 0
        Slot 6 -> Subject 3
        """

        return [
            random.randint(0, self.subject_count - 1)
            for _ in range(self.slot_count)
        ]

    def create_population(self):
        return [
            self.create_chromosome()
            for _ in range(self.population_size)
        ]

    # ---------------------------------------------------------
    # FITNESS FUNCTION
    # ---------------------------------------------------------

    def fitness(self, chromosome):
        """
        Calculate the quality of a schedule.

        Main objectives:

        1. Complete the required study hours.
        2. Prioritize important subjects.
        3. Study subjects before their exams.
        4. Prefer studying closer to the exam.
        5. Penalize studying after an exam.
        6. Penalize unnecessary extra hours.
        7. Avoid putting high-priority subjects too late.
        """

        subject_hours = {
            i: 0
            for i in range(self.subject_count)
        }

        score = 0.0

        # -----------------------------------------------------
        # Count study hours
        # -----------------------------------------------------

        for slot_index, subject_index in enumerate(chromosome):
            slot = self.study_slots[slot_index]

            duration = slot["duration"]

            subject_hours[subject_index] += duration

        # -----------------------------------------------------
        # Required hours
        # -----------------------------------------------------

        for index, subject in enumerate(self.subjects):

            required = subject["hours_needed"]
            studied = subject_hours[index]

            priority = subject["priority"]

            completed_hours = min(studied, required)

            completion_ratio = completed_hours / required

            # Strong reward for completing required hours
            score += (
                completion_ratio
                * priority
                * 100
            )

            # -------------------------------------------------
            # Extra hours penalty
            # -------------------------------------------------

            extra_hours = max(
                0,
                studied - required
            )

            score -= extra_hours * 8

        # -----------------------------------------------------
        # Timing score
        # -----------------------------------------------------

        for slot_index, subject_index in enumerate(chromosome):

            slot = self.study_slots[slot_index]
            subject = self.subjects[subject_index]

            study_time = slot["start"]
            exam_time = subject["exam_date"]

            priority = subject["priority"]

            days_until_exam = (
                exam_time.date() - study_time.date()
            ).days

            # -------------------------------------------------
            # Studying after the exam
            # -------------------------------------------------

            if days_until_exam < 0:

                score -= (
                    priority
                    * 80
                )

                continue

            # -------------------------------------------------
            # Same day as exam
            # -------------------------------------------------

            if days_until_exam == 0:

                score += (
                    priority
                    * 15
                )

                continue

            # -------------------------------------------------
            # Studying before exam
            # -------------------------------------------------

            # Stronger reward when exam is closer.
            #
            # Example:
            #
            # 1 day away -> high reward
            # 10 days away -> smaller reward
            # 30 days away -> very small reward

            timing_reward = (
                priority
                * 30
                / (days_until_exam + 1)
            )

            score += timing_reward

        # -----------------------------------------------------
        # Late-study penalty
        # -----------------------------------------------------

        if self.slot_count > 1:

            for slot_index, subject_index in enumerate(chromosome):

                position_ratio = (
                    slot_index
                    / (self.slot_count - 1)
                )

                if position_ratio > 0.85:

                    subject = self.subjects[subject_index]

                    # This penalty is intentionally mild.
                    # The exam-date logic above is more important.
                    score -= (
                        subject["priority"]
                        * 1.5
                    )

        return score

    # ---------------------------------------------------------
    # SELECTION
    # ---------------------------------------------------------

    def select_parent(self, population, fitness_values):
        """
        Roulette-wheel selection.

        Fitness values can be negative, so they are shifted
        before calculating probabilities.
        """

        minimum = min(fitness_values)

        if minimum <= 0:
            adjusted = [
                fitness - minimum + 1
                for fitness in fitness_values
            ]
        else:
            adjusted = fitness_values[:]

        total = sum(adjusted)

        if total <= 0:
            return random.choice(population)

        return random.choices(
            population,
            weights=adjusted,
            k=1
        )[0]

    # ---------------------------------------------------------
    # CROSSOVER
    # ---------------------------------------------------------

    def crossover(self, parent1, parent2):
        """
        Single-point crossover.
        """

        if len(parent1) < 2:
            return parent1[:], parent2[:]

        break_point = random.randint(
            1,
            len(parent1) - 1
        )

        child1 = (
            parent1[:break_point]
            + parent2[break_point:]
        )

        child2 = (
            parent2[:break_point]
            + parent1[break_point:]
        )

        return child1, child2

    # ---------------------------------------------------------
    # MUTATION
    # ---------------------------------------------------------

    def mutate(self, chromosome):
        """
        Randomly changes subject assignments.

        Mutation never changes the number of study slots.
        """

        mutated = chromosome[:]

        for i in range(len(mutated)):

            if random.random() < self.mutation_rate:

                new_gene = random.randrange(
                    self.subject_count
                )

                # Avoid useless mutation
                if self.subject_count > 1:

                    while new_gene == mutated[i]:
                        new_gene = random.randrange(
                            self.subject_count
                        )

                mutated[i] = new_gene

        return mutated

    # ---------------------------------------------------------
    # NEXT GENERATION
    # ---------------------------------------------------------

    def create_next_generation(
        self,
        population,
        fitness_values
    ):
        """
        Create the next generation using:

        - Elitism
        - Roulette-wheel selection
        - Single-point crossover
        - Mutation
        """

        ranked = sorted(
            zip(population, fitness_values),
            key=lambda x: x[1],
            reverse=True
        )

        new_population = []

        # -----------------------------------------------------
        # Elitism
        # -----------------------------------------------------

        for i in range(self.elitism_count):

            elite = ranked[i][0][:]

            new_population.append(elite)

        # -----------------------------------------------------
        # Generate children
        # -----------------------------------------------------

        while len(new_population) < self.population_size:

            parent1 = self.select_parent(
                population,
                fitness_values
            )

            parent2 = self.select_parent(
                population,
                fitness_values
            )

            child1, child2 = self.crossover(
                parent1,
                parent2
            )

            child1 = self.mutate(child1)

            new_population.append(child1)

            if len(new_population) < self.population_size:

                child2 = self.mutate(child2)

                new_population.append(child2)

        return new_population

    # ---------------------------------------------------------
    # OPTIMIZATION
    # ---------------------------------------------------------

    def optimize(self):
        """
        Run the complete genetic algorithm.

        Returns
        -------
        dict

            {
                "best_chromosome": [...],
                "best_fitness": float,
                "schedule": [...],
                "history": {
                    "best": [...],
                    "average": [...],
                    "worst": [...]
                }
            }
        """

        population = self.create_population()

        best_overall_chromosome = None
        best_overall_fitness = float("-inf")

        for generation in range(self.generations):

            fitness_values = [
                self.fitness(chromosome)
                for chromosome in population
            ]

            best_fitness = max(fitness_values)
            average_fitness = (
                sum(fitness_values)
                / len(fitness_values)
            )
            worst_fitness = min(fitness_values)

            self.best_scores.append(best_fitness)
            self.average_scores.append(average_fitness)
            self.worst_scores.append(worst_fitness)

            # -------------------------------------------------
            # Track best solution ever found
            # -------------------------------------------------

            best_index = fitness_values.index(
                best_fitness
            )

            if best_fitness > best_overall_fitness:

                best_overall_fitness = best_fitness

                best_overall_chromosome = (
                    population[best_index][:]
                )

            # -------------------------------------------------
            # Next generation
            # -------------------------------------------------

            population = self.create_next_generation(
                population,
                fitness_values
            )

        # -----------------------------------------------------
        # Final population evaluation
        # -----------------------------------------------------

        final_fitness_values = [
            self.fitness(chromosome)
            for chromosome in population
        ]

        final_best_index = final_fitness_values.index(
            max(final_fitness_values)
        )

        final_best_fitness = (
            final_fitness_values[final_best_index]
        )

        final_best_chromosome = (
            population[final_best_index]
        )

        # Keep the best solution from the entire run
        if final_best_fitness > best_overall_fitness:

            best_overall_fitness = final_best_fitness

            best_overall_chromosome = (
                final_best_chromosome[:]
            )

        # -----------------------------------------------------
        # Build schedule
        # -----------------------------------------------------

        schedule = self.build_schedule(
            best_overall_chromosome
        )

        return {
            "best_chromosome": best_overall_chromosome,
            "best_fitness": best_overall_fitness,

            "schedule": schedule,

            "history": {
                "best": self.best_scores,
                "average": self.average_scores,
                "worst": self.worst_scores
            },

            "statistics": self.get_statistics(
                best_overall_chromosome
            )
        }

    # ---------------------------------------------------------
    # BUILD SCHEDULE
    # ---------------------------------------------------------

    def build_schedule(self, chromosome):
        """
        Convert a chromosome into UI-friendly schedule data.
        """

        schedule = []

        for slot_index, subject_index in enumerate(chromosome):

            slot = self.study_slots[slot_index]

            subject = self.subjects[subject_index]

            schedule.append(
                {
                    "slot_index": slot_index,

                    "subject_index": subject_index,

                    "subject_name": subject["name"],

                    "priority": subject["priority"],

                    "exam_date": subject["exam_date"].strftime(
                        "%Y-%m-%d"
                    ),

                    "start": slot["start"].strftime(
                        "%Y-%m-%d %H:%M"
                    ),

                    "end": slot["end"].strftime(
                        "%Y-%m-%d %H:%M"
                    ),

                    "duration": slot["duration"]
                }
            )

        return schedule

    # ---------------------------------------------------------
    # STATISTICS
    # ---------------------------------------------------------

    def get_statistics(self, chromosome):
        """
        Generate useful statistics for the UI.
        """

        hours = {
            subject["name"]: 0.0
            for subject in self.subjects
        }

        for slot_index, subject_index in enumerate(chromosome):

            duration = self.study_slots[
                slot_index
            ]["duration"]

            subject_name = self.subjects[
                subject_index
            ]["name"]

            hours[subject_name] += duration

        statistics = []

        for subject in self.subjects:

            name = subject["name"]

            required = subject["hours_needed"]

            studied = hours[name]

            completion = min(
                studied / required,
                1.0
            )

            statistics.append(
                {
                    "subject": name,

                    "required_hours": required,

                    "scheduled_hours": round(
                        studied,
                        2
                    ),

                    "completion_percentage": round(
                        completion * 100,
                        2
                    ),

                    "priority": subject["priority"],

                    "exam_date": subject[
                        "exam_date"
                    ].strftime("%Y-%m-%d")
                }
            )

        return statistics

    # ---------------------------------------------------------
    # OPTIONAL DEBUG OUTPUT
    # ---------------------------------------------------------

    def print_result(self, result):
        """
        Optional console output for testing.

        The UI does NOT need this function.
        """

        print("\n================================")
        print("       BEST SCHEDULE FOUND")
        print("================================")

        print(
            f"Fitness: "
            f"{result['best_fitness']:.2f}"
        )

        print("\nSchedule:")

        for item in result["schedule"]:

            print(
                f"{item['start']} - "
                f"{item['end']} | "
                f"{item['subject_name']}"
            )

        print("\nSubject Statistics:")

        for stat in result["statistics"]:

            print(
                f"{stat['subject']}: "
                f"{stat['scheduled_hours']:.1f}/"
                f"{stat['required_hours']} hours "
                f"({stat['completion_percentage']:.0f}%)"
            )


# =============================================================
# OPTIONAL HELPER FUNCTIONS
# =============================================================

def create_hourly_slots(
    start_date,
    end_date,
    daily_start_hour=9,
    daily_end_hour=18
):
    """
    Convenience function for creating study slots.

    Example:

        slots = create_hourly_slots(
            "2026-09-01",
            "2026-09-10",
            daily_start_hour=9,
            daily_end_hour=18
        )

    This creates one-hour slots from 09:00 to 18:00.

    The UI can eventually generate these automatically.
    """

    start = ExamPlannerGA._parse_datetime(
        start_date,
        date_only=True
    )

    end = ExamPlannerGA._parse_datetime(
        end_date,
        date_only=True
    )

    slots = []

    current_date = start

    while current_date <= end:

        for hour in range(
            daily_start_hour,
            daily_end_hour
        ):

            slot_start = current_date.replace(
                hour=hour,
                minute=0,
                second=0,
                microsecond=0
            )

            slot_end = slot_start + timedelta(
                hours=1
            )

            slots.append(
                {
                    "start": slot_start.strftime(
                        "%Y-%m-%d %H:%M"
                    ),

                    "end": slot_end.strftime(
                        "%Y-%m-%d %H:%M"
                    )
                }
            )

        current_date += timedelta(days=1)

    return slots


# =============================================================
# TEST / DEMO
# =============================================================

if __name__ == "__main__":

    # ---------------------------------------------------------
    # Example subjects
    # ---------------------------------------------------------

    subjects = [
        {
            "name": "Mathematics",
            "priority": 5,
            "hours_needed": 12,
            "exam_date": "2026-09-08"
        },

        {
            "name": "Operating Systems",
            "priority": 4,
            "hours_needed": 10,
            "exam_date": "2026-09-12"
        },

        {
            "name": "Database",
            "priority": 3,
            "hours_needed": 8,
            "exam_date": "2026-09-15"
        },

        {
            "name": "Computer Networks",
            "priority": 4,
            "hours_needed": 10,
            "exam_date": "2026-09-18"
        }
    ]

    # ---------------------------------------------------------
    # Create available study slots
    # ---------------------------------------------------------

    study_slots = create_hourly_slots(
        start_date="2026-09-01",
        end_date="2026-09-18",
        daily_start_hour=9,
        daily_end_hour=15
    )

    # ---------------------------------------------------------
    # Create optimizer
    # ---------------------------------------------------------

    planner = ExamPlannerGA(
        subjects=subjects,
        study_slots=study_slots,

        population_size=40,

        generations=100,

        mutation_rate=0.10,

        elitism_count=2,

        random_seed=42
    )

    # ---------------------------------------------------------
    # Run GA
    # ---------------------------------------------------------

    result = planner.optimize()

    # ---------------------------------------------------------
    # Print result
    # ---------------------------------------------------------

    planner.print_result(result)
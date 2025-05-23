import random
import scheduler_utils as scheduler
import PSO
import copy



class Genetic:
    def __init__(self,mr,cr):
        self.cr = cr
        self.mr = mr
    
    def __iter__(self):
        pass
    
    def generate_population(self, base_schedule, population_size, initialization_type = "random"):
        population = []
        for _ in range(population_size):
            schedule = scheduler.generate_Schedule()
            encoded_schedule = scheduler.encode_Schedule(schedule)
            fitness = scheduler.fitness_function(encoded_schedule, base_schedule)
            if initialization_type == "random":
                individual = PSO.Particle(
                    scheduler.generate_Schedule,
                    scheduler.encode_Schedule,
                    scheduler.decode_Schedule,
                    scheduler.fitness_function
                )
            elif initialization_type == "heuristic":
                individual = PSO.Particle(
                    scheduler.generate_heuristic_schedule,
                    scheduler.encode_Schedule,
                    scheduler.decode_Schedule,
                    scheduler.fitness_function
                )
            elif initialization_type == "weighted":
                individual = PSO.Particle(
                    scheduler.Weighted_generate_Schedule,
                    scheduler.encode_Schedule,
                    scheduler.decode_Schedule,
                    scheduler.fitness_function
                )
            else:
                raise ValueError(f"Unknown initialization_type: '{initialization_type}'")
            individual.position = encoded_schedule
            individual.fitness = fitness
            population.append(individual)
        return population
    
    def uniform_crossover(self, chromosome1, chromosome2):
        new_chromosome = []
        for i in range(len(chromosome1)):
            if random.random() < 0.5:
                new_chromosome.append(chromosome1[i])
            else:
                new_chromosome.append(chromosome2[i])
        return new_chromosome

    def one_point_crossover(self, chromosome1, chromosome2):
        crossover_point = random.randint(0, len(chromosome1) - 1)
        new_chromosome = chromosome1[:crossover_point] + chromosome2[crossover_point:]
        return new_chromosome
    

    def two_point_crossover(self, chromosome1, chromosome2):
        point1 = random.randint(0, len(chromosome1) - 1)
        point2 = random.randint(0, len(chromosome1) - 1)

        if point1 > point2:
            point1, point2 = point2, point1

        new_chromosome = (
            chromosome1[:point1] + chromosome2[point1:point2] + chromosome1[point2:]
        )
        return new_chromosome
    
    
    def sector_based_crossover(self, chromosome1, chromosome2):
        new_chromosome = chromosome1[:]  

        gene_size = 3  
        num_classes = len(chromosome1) // gene_size

        
        sector_length_classes = random.randint(1, num_classes)  
        sector_start_class = random.randint(0, num_classes - 1)
        sector_end_class = (sector_start_class + sector_length_classes) % num_classes

        sector_start_gene = sector_start_class * gene_size
        sector_end_gene = sector_end_class * gene_size

        if sector_start_gene < sector_end_gene:
            new_chromosome[sector_start_gene:sector_end_gene] = chromosome2[sector_start_gene:sector_end_gene]
        else:
            new_chromosome[sector_start_gene:] = chromosome2[sector_start_gene:]
            new_chromosome[:sector_end_gene] = chromosome2[:sector_end_gene]

        return new_chromosome

    def conflict_aware_crossover(self, chromosome1, chromosome2, base_schedule):
        num_classes = len(chromosome1) // 3
        child = chromosome1.copy()

        # Choose crossover range on class level
        cxpoint1 = random.randint(0, num_classes - 2)
        cxpoint2 = random.randint(cxpoint1 + 1, num_classes - 1)

        for i in range(cxpoint1, cxpoint2):
            start = i * 3
            end = start + 3

            # Try taking gene from chromosome2
            candidate_gene = chromosome2[start:end]
            temp_child = child.copy()
            temp_child[start:end] = candidate_gene

            decoded_schedule = scheduler.decode_Schedule(base_schedule, temp_child)
            class_gene = decoded_schedule[i]
            score = self.conflict_score(class_gene, decoded_schedule)

            if score <= 3:
                child[start:end] = candidate_gene
            else:
                # Keep original gene from chromosome1
                child[start:end] = chromosome1[start:end]

        return child


    def random_reinitialization_mutation(self, chromosome, mr):
        new_values = scheduler.encode_Schedule(scheduler.generate_Schedule())
        for i in range(len(chromosome)):
            if random.random() > random.random():
                chromosome[i] = new_values[i]
        return chromosome

    def ranked_selection(self,population,selection_pressure=1.5, maximize=True):
        sorted_pop = sorted(population,key=lambda p: p.get_fitness(),reverse=maximize)
        ranks = range(1,len(sorted_pop)+1)
        probabilities = [
            (2 - selection_pressure) + 2 * (selection_pressure - 1) * (len(sorted_pop) - r) / (len(sorted_pop) - 1)
            for r in ranks
        ]   
        total = sum(probabilities)
        probabilities = [p / total for p in probabilities]
        particle =random.choices(sorted_pop, weights=probabilities, k=1)[0]
        return particle.position

    def tournament_selection(self, population, k=3):
        selected = random.sample(population, k)
        return max(selected, key=lambda p: p.get_fitness()).position

    def update_rates(self,t, t_max):
        ncr = self.cr * (t / t_max)
        nmr = self.mr * ((t_max - t) / t_max)
        return ncr, nmr
    
    def conflict_score(self,class_gene,all_classes):
        score = 0
        for other in all_classes:
            if other == class_gene:
                continue
            if class_gene.get_meetingTime() == other.get_meetingTime():
                if class_gene.get_room() == other.get_room():
                    score += 3
                if class_gene.get_instructor() == other.get_instructor():
                    score += 2
                if class_gene.get_dept() == other.get_dept():
                    score += 1
        if class_gene.get_course().get_num_of_students() > class_gene.get_room().get_seatingCapacity():
            score += 5

        return score
    
    def worst_gene_with_random_gene_mutation(self, chromosome, base_schedule):
        decoded_chromosome = scheduler.decode_Schedule(base_schedule, chromosome)

        worst_gene_index = max(
            range(len(decoded_chromosome)),
            key=lambda i: self.conflict_score(decoded_chromosome[i], decoded_chromosome)
        )

        start = worst_gene_index * 3
        end = start + 3

        random_schedule = scheduler.generate_Schedule()
        random_encoded = scheduler.encode_Schedule(random_schedule)

        new_chromosome = chromosome.copy()
        new_chromosome[start:end] = random_encoded[start:end] 
        return new_chromosome
    
    

    def swap_class_assignments_mutation(self,chromosome):
        random_schedule = scheduler.generate_Schedule()
        new_chromosome = scheduler.encode_Schedule(random_schedule)
        num_classes = len(chromosome) // 3

        idx1 = random.randint(0, num_classes - 1)
        idx2 = random.randint(0, num_classes - 1)
        while idx1 == idx2:
            idx2 = random.randint(0, num_classes - 1)

        start1, start2 = idx1 * 3, idx2 * 3

        for i in range(3):
            chromosome[start1 + i], chromosome[start2 + i] = (
                new_chromosome[start2 + i],
                new_chromosome[start1 + i],
            )

        return chromosome

    def field_mutation(self, chromosome):
        random_schedule = scheduler.generate_Schedule()
        new_chromosome = scheduler.encode_Schedule(random_schedule)
        num_classes = len(chromosome) // 3

        class_idx = random.randint(0, num_classes - 1)
        gene_start = class_idx * 3

        field = random.randint(0, 2)

        if field == 0:
            chromosome[gene_start] = new_chromosome[gene_start]
        elif field == 1:
            chromosome[gene_start + 1] = new_chromosome[gene_start + 1]
        elif field == 2:
            chromosome[gene_start + 2] = new_chromosome[gene_start + 2]

        return chromosome
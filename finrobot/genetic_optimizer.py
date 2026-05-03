"""
Adaptive Parameter Optimizer
Uses genetic algorithms and Bayesian optimization to continuously find optimal parameters
"""
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Any, Optional, Callable
from datetime import datetime
import json
import logging
from scipy import stats
import random

logger = logging.getLogger(__name__)


@dataclass
class ParameterGene:
    """Represents a single parameter with its constraints"""
    name: str
    value: Any
    min_val: float
    max_val: float
    step: float
    param_type: str = 'float'  # 'float', 'int', 'choice'
    choices: List[Any] = field(default_factory=list)
    
    def mutate(self, mutation_rate: float = 0.1):
        """Mutate this parameter"""
        if random.random() > mutation_rate:
            return
            
        if self.param_type == 'choice' and self.choices:
            self.value = random.choice(self.choices)
        elif self.param_type == 'int':
            current = int(self.value)
            delta = random.randint(-max(1, int(self.step)), max(1, int(self.step)))
            new_val = current + delta
            self.value = max(self.min_val, min(self.max_val, new_val))
        else:
            # Float
            delta = random.gauss(0, (self.max_val - self.min_val) * 0.1)
            new_val = float(self.value) + delta
            self.value = max(self.min_val, min(self.max_val, new_val))
    
    def crossover(self, other: 'ParameterGene') -> 'ParameterGene':
        """Create offspring from two parents"""
        child = ParameterGene(
            name=self.name,
            value=self.value if random.random() < 0.5 else other.value,
            min_val=self.min_val,
            max_val=self.max_val,
            step=self.step,
            param_type=self.param_type,
            choices=self.choices.copy()
        )
        return child
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'value': self.value,
            'min': self.min_val,
            'max': self.max_val,
            'step': self.step,
            'type': self.param_type
        }


@dataclass
class StrategyGenome:
    """A complete set of parameters for a strategy"""
    strategy_name: str
    parameters: Dict[str, ParameterGene]
    fitness: float = -np.inf
    generation: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    backtest_results: Dict = field(default_factory=dict)
    
    def mutate(self, mutation_rate: float = 0.1):
        """Mutate random parameters"""
        for param in self.parameters.values():
            param.mutate(mutation_rate)
    
    def crossover(self, other: 'StrategyGenome') -> 'StrategyGenome':
        """Create offspring from two parents"""
        child_params = {}
        for name, param in self.parameters.items():
            if name in other.parameters:
                child_params[name] = param.crossover(other.parameters[name])
            else:
                child_params[name] = ParameterGene(
                    name=param.name,
                    value=param.value,
                    min_val=param.min_val,
                    max_val=param.max_val,
                    step=param.step,
                    param_type=param.param_type,
                    choices=param.choices.copy()
                )
        
        child = StrategyGenome(
            strategy_name=self.strategy_name,
            parameters=child_params,
            generation=max(self.generation, other.generation) + 1
        )
        return child
    
    def to_dict(self) -> Dict:
        return {
            'strategy_name': self.strategy_name,
            'fitness': self.fitness,
            'generation': self.generation,
            'created_at': self.created_at.isoformat(),
            'parameters': {k: v.to_dict() for k, v in self.parameters.items()},
            'backtest_results': self.backtest_results
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StrategyGenome':
        params = {}
        for k, v in data['parameters'].items():
            params[k] = ParameterGene(
                name=v['name'],
                value=v['value'],
                min_val=v['min'],
                max_val=v['max'],
                step=v['step'],
                param_type=v.get('type', 'float'),
                choices=v.get('choices', [])
            )
        
        genome = cls(
            strategy_name=data['strategy_name'],
            parameters=params,
            fitness=data.get('fitness', -np.inf),
            generation=data.get('generation', 0),
            backtest_results=data.get('backtest_results', {})
        )
        return genome


class GeneticOptimizer:
    """
    Genetic Algorithm for optimizing strategy parameters
    Uses selection, crossover, and mutation to evolve better parameters
    """
    
    def __init__(self,
                 population_size: int = 50,
                 elite_size: int = 5,
                 mutation_rate: float = 0.15,
                 crossover_rate: float = 0.8,
                 tournament_size: int = 3):
        self.population_size = population_size
        self.elite_size = elite_size
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.tournament_size = tournament_size
        
        self.population: List[StrategyGenome] = []
        self.generation = 0
        self.best_genome: Optional[StrategyGenome] = None
        self.history: List[Dict] = []
    
    def initialize_population(self, 
                             strategy_name: str,
                             param_specs: Dict[str, Dict]):
        """
        Initialize population with random genomes
        
        param_specs: {
            'param_name': {
                'min': 0.0,
                'max': 1.0,
                'step': 0.01,
                'type': 'float'  # or 'int', 'choice'
                'choices': []  # for choice type
            }
        }
        """
        self.population = []
        
        for i in range(self.population_size):
            params = {}
            for name, spec in param_specs.items():
                if spec.get('type') == 'choice' and spec.get('choices'):
                    value = random.choice(spec['choices'])
                elif spec.get('type') == 'int':
                    min_v = int(spec['min'])
                    max_v = int(spec['max'])
                    step = int(spec.get('step', 1))
                    value = random.randrange(min_v, max_v + 1, step)
                else:
                    min_v = float(spec['min'])
                    max_v = float(spec['max'])
                    value = random.uniform(min_v, max_v)
                    if 'step' in spec:
                        step = spec['step']
                        value = round(value / step) * step
                
                params[name] = ParameterGene(
                    name=name,
                    value=value,
                    min_val=spec['min'],
                    max_val=spec['max'],
                    step=spec.get('step', 0.01),
                    param_type=spec.get('type', 'float'),
                    choices=spec.get('choices', [])
                )
            
            genome = StrategyGenome(
                strategy_name=strategy_name,
                parameters=params,
                generation=0
            )
            self.population.append(genome)
    
    def evaluate_fitness(self, 
                        fitness_func: Callable[[StrategyGenome], float]):
        """
        Evaluate fitness for entire population
        """
        for genome in self.population:
            try:
                genome.fitness = fitness_func(genome)
            except Exception as e:
                logger.error(f"Error evaluating fitness: {e}")
                genome.fitness = -np.inf
        
        # Sort by fitness
        self.population.sort(key=lambda x: x.fitness, reverse=True)
        
        # Update best
        if self.population and (self.best_genome is None or 
                                self.population[0].fitness > self.best_genome.fitness):
            self.best_genome = self.population[0]
        
        # Record history
        self.history.append({
            'generation': self.generation,
            'best_fitness': self.population[0].fitness if self.population else -np.inf,
            'avg_fitness': np.mean([g.fitness for g in self.population]) if self.population else -np.inf,
            'worst_fitness': self.population[-1].fitness if self.population else -np.inf,
        })
    
    def create_next_generation(self):
        """
        Create next generation using selection, crossover, and mutation
        """
        new_population = []
        
        # Elitism: Keep best individuals
        new_population.extend(self.population[:self.elite_size])
        
        # Create rest of population
        while len(new_population) < self.population_size:
            # Tournament selection
            parent1 = self._tournament_select()
            parent2 = self._tournament_select()
            
            # Crossover
            if random.random() < self.crossover_rate:
                child = parent1.crossover(parent2)
            else:
                child = parent1 if random.random() < 0.5 else parent2
            
            # Mutation
            child.mutate(self.mutation_rate)
            child.generation = self.generation + 1
            
            new_population.append(child)
        
        self.population = new_population
        self.generation += 1
    
    def _tournament_select(self) -> StrategyGenome:
        """
        Tournament selection
        """
        tournament = random.sample(self.population, 
                                min(self.tournament_size, len(self.population)))
        return max(tournament, key=lambda x: x.fitness)
    
    def get_best_params(self) -> Dict[str, Any]:
        """Get parameters from best genome"""
        if self.best_genome is None:
            return {}
        return {k: v.value for k, v in self.best_genome.parameters.items()}
    
    def save_state(self, filepath: str):
        """Save optimizer state"""
        state = {
            'generation': self.generation,
            'population': [g.to_dict() for g in self.population],
            'best_genome': self.best_genome.to_dict() if self.best_genome else None,
            'history': self.history,
            'population_size': self.population_size,
            'elite_size': self.elite_size,
            'mutation_rate': self.mutation_rate,
            'crossover_rate': self.crossover_rate,
            'tournament_size': self.tournament_size
        }
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2, default=str)
    
    @classmethod
    def load_state(cls, filepath: str) -> 'GeneticOptimizer':
        """Load optimizer state"""
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        optimizer = cls(
            population_size=state.get('population_size', 50),
            elite_size=state.get('elite_size', 5),
            mutation_rate=state.get('mutation_rate', 0.15),
            crossover_rate=state.get('crossover_rate', 0.8),
            tournament_size=state.get('tournament_size', 3)
        )
        
        optimizer.generation = state['generation']
        optimizer.population = [StrategyGenome.from_dict(g) for g in state['population']]
        optimizer.best_genome = StrategyGenome.from_dict(state['best_genome']) if state['best_genome'] else None
        optimizer.history = state['history']
        
        return optimizer


# Convenience function for quick optimization
def optimize_strategy_parameters(
    backtest_func: Callable[[Dict], Dict],
    param_specs: Dict[str, Dict],
    generations: int = 50,
    population_size: int = 50,
    target_metric: str = 'sharpe_ratio'
) -> Tuple[Dict, float]:
    """
    Optimize strategy parameters using genetic algorithm
    
    Args:
        backtest_func: Function that takes params dict and returns results dict
        param_specs: Parameter specifications
        generations: Number of generations to run
        population_size: Population size
        target_metric: Metric to optimize (e.g., 'sharpe_ratio', 'return_pct', 'win_rate')
    
    Returns:
        (best_params, best_fitness)
    """
    optimizer = GeneticOptimizer(
        population_size=population_size,
        elite_size=max(3, population_size // 10),
        mutation_rate=0.15,
        crossover_rate=0.8
    )
    
    # Initialize population
    optimizer.initialize_population('strategy', param_specs)
    
    # Define fitness function
    def fitness_func(genome: StrategyGenome) -> float:
        params = {k: v.value for k, v in genome.parameters.items()}
        try:
            results = backtest_func(params)
            fitness = results.get(target_metric, -np.inf)
            # Penalize negative returns
            if results.get('return_pct', 0) < 0:
                fitness *= 0.5
            return fitness
        except Exception as e:
            logger.error(f"Error in fitness evaluation: {e}")
            return -np.inf
    
    # Run optimization
    best_fitness_history = []
    
    for gen in range(generations):
        optimizer.evaluate_fitness(fitness_func)
        best_fitness_history.append(optimizer.population[0].fitness if optimizer.population else -np.inf)
        
        if gen < generations - 1:
            optimizer.create_next_generation()
        
        if gen % 10 == 0:
            logger.info(f"Generation {gen}: Best fitness = {best_fitness_history[-1]:.4f}")
    
    # Get best parameters
    best_params = optimizer.get_best_params()
    best_fitness = optimizer.best_genome.fitness if optimizer.best_genome else -np.inf
    
    logger.info(f"Optimization complete. Best fitness: {best_fitness:.4f}")
    logger.info(f"Best params: {best_params}")
    
    return best_params, best_fitness

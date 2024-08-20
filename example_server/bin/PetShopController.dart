import 'generated.dart';
import 'Animal.dart';
import 'package:uuid/uuid.dart';

final PET_NAMES = ['Abigail', 'Ace', 'Adam', 'Addie', 'Admiral', 'Aggie', 'Aires', 'Aj', 'Ajax', 'Aldo', 'Alex', 'Alexus', 'Alf', 'Alfie', 'Allie', 'Ally', 'Amber', 'Amie', 'Amigo', 'Amos', 'Amy', 'Andy', 'Angel', 'Angus', 'Annie', 'Apollo', 'April', 'Archie', 'Argus', 'Aries', 'Armanti', 'Arnie', 'Arrow', 'Ashes', 'Ashley', 'Astro', 'Athena', 'Atlas', 'Audi', 'Augie', 'Aussie', 'Austin', 'Autumn', 'Axel', 'Axle', 'Babbles', 'Babe', 'Baby', 'Baby-doll', 'Babykins', 'Bacchus', 'Bailey', 'Bam-bam', 'Bambi', 'Bandit', 'Banjo', 'Barbie', 'Barclay', 'Barker', 'Barkley', 'Barley', 'Barnaby', 'Barney', 'Baron', 'Bart', 'Basil', 'Baxter', 'Bb', 'Beamer', 'Beanie', 'Beans', 'Bear', 'Beau', 'Beauty', 'Beaux', 'Bebe', 'Beetle', 'Bella', 'Belle', 'Ben', 'Benji', 'Benny', 'Benson', 'Bentley', 'Bernie', 'Bessie', 'Biablo', 'Bibbles', 'Big Boy', 'Big Foot', 'Biggie', 'Billie', 'Billy', 'Bingo', 'Binky', 'Birdie', 'Birdy', 'Biscuit', 'Bishop', 'Gus', 'Guy', 'Gypsy', 'Hailey', 'Haley', 'Hallie', 'Hamlet', 'Hammer', 'Hank', 'Hanna', 'Hannah', 'Hans', 'Happy', 'Hardy', 'Harley', 'Harpo', 'Harrison', 'Harry', 'Harvey', 'Heather', 'Heidi', 'Henry', 'Hercules', 'Hershey', 'Higgins', 'Hobbes', 'Holly', 'Homer', 'Honey', 'Honey-Bear', 'Hooch', 'Hoover', 'Hope', 'Houdini', 'Howie', 'Hudson', 'Huey', 'Hugh', 'Hugo', 'Humphrey', 'Hunter', 'India', 'Indy', 'Iris', 'Isabella', 'Isabelle', 'Itsy', 'Itsy-bitsy', 'Ivory', 'Ivy', 'Izzy', 'Jack', 'Jackie', 'Jackpot', 'Jackson', 'Jade', 'Jagger', 'Jags', 'Jaguar', 'Jake', 'Jamie', 'Jasmine', 'Jasper', 'Jaxson', 'Jazmie', 'Jazz', 'Jelly', 'Jelly-bean', 'Jenna', 'Jenny', 'Jerry', 'Jersey', 'Jess', 'Jesse', 'Jesse James', 'Jessie', 'Jester', 'Jet', 'Jethro', 'Jett', 'Jetta', 'Jewel', 'Jewels', 'Jimmy', 'Jingles', 'JJ', 'Joe', 'Joey', 'Johnny', 'Jojo', 'Joker', 'Jolie', 'Jolly', 'Jordan', 'Josie', 'Joy', 'JR', 'Judy', 'Julius', 'June', 'Misty', 'Mitch', 'Mittens', 'Mitzi', 'Mitzy', 'Mo', 'Mocha', 'Mollie', 'Molly', 'Mona', 'Muffy', 'Nakita', 'Nala', 'Nana', 'Natasha', 'Nellie', 'Nemo', 'Nena', 'Peanut', 'Peanuts', 'Pearl', 'Pebbles', 'Penny', 'Phoebe', 'Phoenix', 'Sara', 'Sarah', 'Sasha', 'Sassie', 'Sassy', 'Savannah', 'Scarlett', 'Shasta', 'Sheba', 'Sheena', 'Shelby', 'Shelly', 'Sienna', 'Sierra', 'Silky', 'Silver', 'Simone', 'Sissy', 'Skeeter', 'Sky', 'Skye', 'Skyler', 'Waldo', 'Wallace', 'Wally', 'Walter', 'Wayne', 'Weaver', 'Webster', 'Wesley', 'Westie'];

class PetShopController implements APIHandler {
  final List<Animal> animals;
  static PetShopController? _instance;
  PetShopController._(this.animals);

  static List<Animal> _generateRandomAnimals(int length, {AnimalType? type}) {
    final types = AnimalType.values.toList();
    // Shuffle runs in-place so can't do List.generate(), have to get old-fashioned
    final out = <Animal>[];
    for (var i = 0; i < length; i++) {
      types.shuffle();
      PET_NAMES.shuffle();
      out.add(Animal(uuid: Uuid().v4(), type: type ?? types.first, name: PET_NAMES.first));
    }
    return out;
  }

  factory PetShopController() => _instance ??= PetShopController._(_generateRandomAnimals(15));

  Map<AnimalType, int> getAvailableAnimalStock() {
    return animals.fold(<AnimalType, int>{}, (counts, current) {
      counts[current.type] = (counts[current.type] ?? 0) + 1;
      return counts;
    });
  }

  void addAnimalStock(Map<AnimalType, int> newAnimals) {
    newAnimals.forEach((type, count) => animals.addAll(_generateRandomAnimals(count, type: type)));
  }

  Animal getAnimalByUuid(String uuid) {
    final out = animals.where((animal) => animal.uuid == uuid).toList();
    if (out.isEmpty) throw APIException.UnknownUuidWhileGettingAnimal;
    return out.first;
  }

  Animal buyAnimal(AnimalType type) {
    if (getAvailableAnimalStock()[type] == 0) throw APIException.OutOfStock;
    final animal = animals.firstWhere((animal) => animal.type == type);
    animals.remove(animal);
    return animal;
  }
}
import 'generated.dart';
import 'dart:io';
import '../../auth.dart';
import 'package:uuid/uuid.dart';

String getString(String msg) {
  String? out;
  while (out == null) {
    stdout.write('$msg: ');
    out = stdin.readLineSync();
  }
  return out;
}

int getInt(String msg) {
  int? out;
  while (out == null) {
    stdout.write('$msg: ');
    out = int.tryParse(stdin.readLineSync() ?? '');
  }
  return out;
}

T valueChoice<T>(String msg, List<T> values, String Function(T) toString, {String Function(T)? additionalInfo}) {
  var choice = 0;
  print('$msg: ');
  for (var (i, value) in values.indexed) {
    print('${i + 1}. ${toString(value)}${additionalInfo == null ? '' : ' ${additionalInfo.call(value)}'}');
  }
  while (choice < 1 || choice > values.length) {
    choice = getInt('Ener the number for your choice');
  }
  return values[choice - 1];
}

bool optionChoice(String msg) => valueChoice(msg, [true, false], (val) => val ? 'Yes' : 'No');

Future doClient() async {
  print('You are a client at the pet shop!');
  final stock = await API.getAvailableAnimalStock();
  final animalType = valueChoice('Choose your animal', AnimalType.values, AnimalTypeToString, additionalInfo: (type) => '(${stock[type]} available)');
  final myPet = await API.buyAnimal(animalType);
  print('Meet your new ${AnimalTypeToString(myPet.type)}, ${myPet.name}!');
  print("Let's give ${myPet.name} some food :)");
  final food = valueChoice('What food do you want to feed your new pet', FoodType.values, FoodTypeToString);
  try {
    myPet.feed(food);
  } on APIException catch (e) {
    if (e == APIException.AnimalDied) {
      print('Yeouch! You killed ${myPet.name} the ${myPet.type} by feeding them ${FoodTypeToString(food)} :(');
    }
  }
}

Future<User> getUser() async {
  final users = await API.getAllUsers();
  final uname = valueChoice<String>('Enter username', users.keys.toList(), (s) => s);
  return users[uname]!;
}

Future doStaff() async {
  final uname = getString('Username');
  final pwd = getString('Password');
  final pwdHash = hashPassword(pwd, await API.getSaltForUser(uname));
  await API.authorize(AuthorisationRequest(username: uname, passwordHash: pwdHash));
  final currentUser = await API.getCurrentUser();
  print('You are logged in as ${currentUser.username} (auth level ${AuthLevelToString(currentUser.authLevel)})');
  var moreActions = true;
  while (moreActions) {
    final action = valueChoice('What action would you like to take', StaffAction.values, StaffActionToString);
    switch (action) {
      case StaffAction.AddAnimalStock: {
        final stock = await API.getAvailableAnimalStock();
        final newAnimals = {for (var type in AnimalType.values) type: 0};
        var addMore = true;
        while (addMore) {
          final animal = valueChoice('Which animal type would you like to add more of', AnimalType.values, AnimalTypeToString, additionalInfo: (type) => '(${stock[type]} in stock, adding ${newAnimals[type]})');
          newAnimals[animal] = getInt('How many would you like to add');
          addMore = optionChoice('Would you like to continue adding animals:');
        }
        await API.addAnimalStock(newAnimals);
        print('New stock: ${await API.getAvailableAnimalStock()}');
      }
      case StaffAction.ChangeMyPassword: {
        final newPassword = getString('Enter new password');
        final newSalt = Uuid().v4();
        await API.changeUserPassword(ChangePasswordRequest(username: currentUser.username, passwordHash: hashPassword(newPassword, newSalt), newSalt: newSalt));
      }
      case StaffAction.AddUser: {
        final username = getString('New username');
        final pwd = getString('New password');
        final salt = Uuid().v4();
        final authLevel = valueChoice('New authorization level', AuthLevel.values, AuthLevelToString);
        final newUser = User(uuid: '', authLevel: authLevel, username: username, passwordHash: hashPassword(pwd, salt), salt: salt);
        print('Adding user ${newUser.toString()}');
        await API.addUser(newUser);
      }
      case StaffAction.DeleteUser: {
        final user = await getUser();
        final uuid = user.uuid;
        if (optionChoice('Are you sure')) { await API.deleteUser(uuid); }
      }
      case StaffAction.EditUserAuthLevel: {
        final user = await getUser();
        print('Current auth level: ${user.authLevel}');
        final newAuthLevel = await valueChoice('Enter new auth level', AuthLevel.values, AuthLevelToString);
        await API.editUser(user.copyWith(authLevel: newAuthLevel));
      }
      case StaffAction.EditUserPassword: {
        final user = await getUser();
        final newPassword = getString('Enter new password');
        final salt = Uuid().v4();
        await API.editUser(user.copyWith(passwordHash: hashPassword(newPassword, salt), salt: salt));
      }
      case StaffAction.Exit: {
        moreActions = false;
      }
    }
  }
}

Future main() async {
  if (optionChoice('Would you like to login as a staff member')) await doStaff(); else await doClient();
}

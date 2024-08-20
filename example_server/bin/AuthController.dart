import 'dart:convert';
import 'dart:io';
import 'generated.dart';
import 'package:uuid/uuid.dart';
import '../../auth.dart';

class AuthInfo {
  final User user;
  DateTime tokenLastActive;

  AuthInfo({required this.user, required this.tokenLastActive});

  @override
  String toString() => '${user.username} @ $tokenLastActive';
}

class AuthController extends AuthHandler {
  static AuthController? _instance;

  AuthController._({required this.fname}) : _file = _load(fname);

  factory AuthController() {
    return _instance ??= AuthController._(fname: 'users.json');
  }

  static UsersInfo _load(String fname) => UsersInfo.fromJson(jsonDecode(File(fname).readAsStringSync()));

  final String fname;
  UsersInfo _file;

  void save() {
   File(fname).writeAsStringSync(JsonEncoder.withIndent('    ').convert(_file.toJson()));
  }

  final loggedIn = <String, AuthInfo>{};

  Map<String, User> getAllUsers() => _file.users;

  User getUserByUsername(String username) {
    final user = getAllUsers()[username];
    if (user == null) throw APIException.UnknownUsernameWhileGettingUser;
    return user;
  }

  String getSaltForUser(String username) => getUserByUsername(username).salt;
  
  String generateToken(AuthorisationRequest credentials) {
    print(credentials.passwordHash);
    final user = getUserByUsername(credentials.username);

    if (user.passwordHash != credentials.passwordHash) throw APIException.IncorrectCredentials;

    final token = Uuid().v4();
    loggedIn[token] = AuthInfo(user: user, tokenLastActive: DateTime.now());
    print('$token for ${credentials.username}');
    return token;
  }

  AuthLevel validateToken(String token) {
    final authInfo = loggedIn[token];
    if (authInfo == null) return AuthLevel.Unauthorized;
    if (DateTime.now().difference(authInfo.tokenLastActive) > Duration(minutes: 30)) {
      loggedIn.remove(token);
      throw APIException.LoginPeriodTimedOut;
    }
    authInfo.tokenLastActive = DateTime.now();
    return authInfo.user.authLevel;
  }

  void logoutUser(String username) {
    loggedIn.removeWhere((_, info) => info.user.username == username);
  }

  User getUserByUuid(String uuid) {
    for (var user in getAllUsers().values) {
      if (user.uuid == uuid) return user;
    }
    throw APIException.UnknownUuidWhileGettingUser;
  }

  User getCurrentUser(String token) {
    if (!loggedIn.containsKey(token)) throw APIException.NotLoggedIn;
    return loggedIn[token]!.user;
  }

  void validateUser(User user) {
    if (user.username.isEmpty) throw APIException.UsernameIsEmpty;
    if (user.passwordHash == hashPassword('', user.salt)) throw APIException.PasswordIsEmpty;
  }

  void addUser(User user) {
    if (user.uuid != '') throw APIException.TriedToAddUserWithNonEmptyUuid;
    if (getAllUsers().containsKey(user.username)) throw APIException.UsernameAlreadyExists;
    validateUser(user);
    _file.users[user.username] = user.copyWith(uuid: Uuid().v4());
    save();
  }

  void deleteUser(String uuid) {
    for (var username in getAllUsers().keys) {
      if (getUserByUsername(username).uuid == uuid) {
        logoutUser(getUserByUuid(uuid).username);
        _file.users.remove(username);
        save();
        return;
      }
    }
    throw APIException.UnknownUuidWhileDeletingUser;
  }

  void editUser(User user) {
    if (getAllUsers().containsKey(user.username)) {
      final userOnFileWithUsername = getUserByUsername(user.username);
      if (user.uuid != userOnFileWithUsername.uuid) {
        // changed the username to something that already exists
        // (we won't give a fuck about this after the uuid refactor that's DEFINITELY HAPPENING SOON)
        throw APIException.UsernameAlreadyExists;
      }
    }
    validateUser(user);
    logoutUser(getUserByUuid(user.uuid).username);
    deleteUser(user.uuid);
    _file.users[user.username] = user;
    save();
  }

  void changeUserPassword(ChangePasswordRequest request) {
    if (!_file.users.containsKey(request.username)) throw APIException.UnknownUsernameWhileChangingPassword;
    if (request.passwordHash == hashPassword('', request.newSalt)) throw APIException.PasswordIsEmpty;
    logoutUser(request.username);
    _file.users[request.username] = _file.users[request.username]!.copyWith(salt: request.newSalt, passwordHash: request.passwordHash);
    logoutUser(request.username);
    save();
  }

  // Admins can use editUser to change anyone's password, this endpoint for changing your own
  bool changeUserPasswordAuth(String token, ChangePasswordRequest request) {
    final loggedInUser = loggedIn[token];
    if (loggedInUser == null) return false;
    return request.username == loggedInUser.user.username;
  }
}
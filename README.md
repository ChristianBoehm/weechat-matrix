[![license](https://img.shields.io/badge/license-ISC-blue.svg?style=flat-square)](LICENSE)

# weechat-matrix

A [Weechat](https://weechat.org/) script for the [Matrix](https://matrix.org/)
protocol, with end-to-end encryption.

> **Maintained fork** of [poljar/weechat-matrix](https://github.com/poljar/weechat-matrix)
> by Damir Jelić, which has had no commits since July 2023. This fork keeps the
> script working with current homeservers and Element, and is a drop-in
> replacement for the upstream version.

## What's new in this fork

| Version | Changes |
|---|---|
| 0.3.4 | `matrix.network.auto_ignore_new_devices`: encrypt for new devices of other users without asking, like Element (own devices still need a decision) |
| 0.3.3 | `/olm backup restore`: unlock old encrypted messages from the server-side key backup |
| 0.3.2 | `/olm cross-sign`: the device signs itself with the recovery key and shows as verified in Element · modern verification request flow · automatic re-upload of device keys the server lost |
| 0.3.1 | SSO sessions survive restarts · `python-future` optional · helpers work on BusyBox/Alpine |

## Project status

Stable and usable as a daily driver. The fork is in maintenance mode: fixes
and focused features that keep it working with current Matrix clients. Not
implemented: verifying *other* users via cross-signing, uploading to the key
backup, and session unwedging.

The upstream author's Rust rewrite,
[weechat-matrix-rs](https://github.com/poljar/weechat-matrix-rs), is under
active development but, by its own description, still a work in progress
without releases.

# Prerequisites

weechat-matrix is a Weechat *script*, not a standalone chat client: it runs
inside [Weechat](https://weechat.org/) and therefore requires a Weechat
installation **with Python 3 support** as a hard prerequisite.

Check your Weechat build with:

    weechat --build-info

and make sure it reports `ENABLE_PYTHON: ON`. The Python plugin must use the
same Python interpreter you install the dependencies with; check the runtime
version inside Weechat with `/python version`.

# Installation

The distribution packages below ship the 2023 upstream version, without the
fixes of this fork; use [Other platforms](#other-platforms) to install the
fork, then copy its files over the packaged ones or run it from git.

## Arch Linux

Packaged as `community/weechat-matrix`.

    pacman -S weechat-matrix

## Alpine Linux

    apk add weechat-matrix

Then follow the instructions printed during installation to make the script
available to weechat.

## Other platforms

1. Install libolm 3.1+

    - Debian 11+ (testing/sid) or Ubuntu 19.10+ install libolm-dev

    - FreeBSD `pkg install olm`

    - macOS `brew install libolm`

    - Failing any of the above see https://gitlab.matrix.org/matrix-org/olm
      for instructions about building it from sources

2. Clone the repo and install dependencies
    ```
    git clone https://github.com/ChristianBoehm/weechat-matrix.git
    cd weechat-matrix
    pip install --user -r requirements.txt
    ```

    The `python-future` package listed in `requirements.txt` is only required
    for very old Python versions; on Python 3 the script falls back to native
    standard-library equivalents, so it also works where `future` is not
    installed (e.g. the Alpine Linux package).

3. As your regular user, just run: `make install` in this repository directory.

    This installs the main python file (`main.py`) into
    `~/.weechat/python/` (renamed to `matrix.py`) along with the other
    python files it needs (from the `matrix` subdir).

    Note that weechat only supports Python2 OR Python3, and that setting is
    determined at the time that Weechat is compiled.  Weechat-Matrix can work with
    either Python2 or Python3, but when you install dependencies you will have to
    take into account which version of Python your Weechat was built to use.

    The minimal supported python2 version is 2.7.10.

    The minimal supported python3 version is 3.5.4 or 3.6.1.

    To check the python version that weechat is using, run:

       /python version

## Using virtualenv
If you want to install dependencies inside a virtualenv, rather than
globally for your system or user, you can use a virtualenv.
Weechat-Matrix will automatically use any virtualenv it finds in a
directory called `venv` next to its main Python file (after resolving
symlinks). Typically, this means `~/.weechat/python/venv`.

To create such a virtualenv, you can use something like below. This only
needs to happen once:

```
virtualenv ~/.weechat/python/venv
```

Then, activate the virtualenv:

```
. ~/.weechat/python/venv/bin/activate
```

This needs to be done whenever you want to install packages inside the
virtualenv (so before running the `pip install` command documented
above.


Once the virtualenv is prepared in the right location, Weechat-Matrix
will automatically activate it when the script is loaded. This should
not affect other script, which seem to have a separate Python
environment.

Note that this only supports virtualenv tools that support the
[`activate_this.py` way of
activation](https://virtualenv.pypa.io/en/latest/userguide/#using-virtualenv-without-bin-python).
This includes the `virtualenv` command, but excludes pyvenv and the
Python3 `venv` module. In particular, this works if (for a typical
installation of `matrix.py`) the file
`~/.weechat/python/venv/bin/activate_this.py` exists.

## Run from git directly

Rather than copying files into `~/.weechat` (step 3 above), it is also
possible to run from a git checkout directly using symlinks.

For this, you need two symlinks:

```
ln -s /path/to/weechat-matrix/main.py ~/.weechat/python/matrix.py
ln -s /path/to/weechat-matrix/matrix ~/.weechat/python/matrix
```

This first link is the main python file, that can be loaded using
`/script load matrix.py`. The second link is to the directory with extra
python files used by the main script. This directory must be linked as
`~/.weechat/python/matrix` so it ends up in the python library path and
its files can be imported using e.g. `import matrix` from the main python
file.

Note that these symlinks are essentially the same as the files that
would have been copied using `make install`.

## Uploading files

Uploads are done using a helper script, which is found under
[contrib/matrix_upload](contrib/matrix_upload.py).
We recommend you install this under your `PATH` as `matrix_upload` (without the `.py` suffix).
Uploads can be done from Weechat with: `/upload <file>`.

## Downloading encrypted files

Encrypted files are displayed as an `emxc://` URI which cannot be directly
opened. They can be opened in two different ways:

- **In the CLI** by running the
[contrib/matrix_decrypt](contrib/matrix_decrypt.py)
helper script.

- **In the browser** by using
  [matrix-decryptapp](https://github.com/seirl/matrix-decryptapp). This is a
  static website which cannot see your data, all the decryption happens
  on the client side. You can either host it yourself or directly use the
  instance hosted on `seirl.github.io`. This weechat trigger will convert all
  your `emxc://` URLs into clickable https links:

  ```
  /trigger addreplace emxc_decrypt modifier weechat_print "" ";($|[^\w/#:\[])(emxc://([^ ]+));${re:1}https://seirl.github.io/matrix-decryptapp/#${re:2};"
  ```

# Configuration

Configuration is completed primarily through the Weechat interface.  First start Weechat, and then issue the following commands:

1. Start by loading the Weechat-Matrix script:

       /script load matrix.py

2. Now set your username and password:

       /set matrix.server.matrix_org.username johndoe
       /set matrix.server.matrix_org.password jd_is_awesome

3. Now try to connect:

       /matrix connect matrix_org

4. Automatically load the script

       $ ln -s ../matrix.py ~/.weechat/python/autoload

5. Automatically connect to the server

       /set matrix.server.matrix_org.autoconnect on

6. If everything works, save the configuration

       /save

## For using a custom (not matrix.org) matrix server:

1. Add your custom server to the script:

       /matrix server add myserver myserver.org

1. Add the appropriate credentials

       /set matrix.server.myserver.username johndoe
       /set matrix.server.myserver.password jd_is_awesome

1. If everything works, save the configuration

       /save

## Single sign-on:

Single sign-on is supported using a helper script, the script found under
[contrib/matrix_sso_helper](contrib/matrix_sso_helper.py)
should be installed under your `PATH` as `matrix_sso_helper` (without the `.py` suffix).

For single sign-on to be the preferred leave the servers username and password
empty.

After connecting a URL will be presented which needs to be used to perform the
sign on. Please note that the helper script spawns a HTTP server which waits for
the sign-on token to be passed back. This makes it necessary to do the sign on
on the same host as Weechat. The helper also works on systems with a
non-GNU userland (e.g. BusyBox on Alpine Linux).

Since v0.3.1 the access token received at login is stored in the server's
session directory (file `access_token`, mode 0600, next to the end-to-end
encryption database). On the next start weechat-matrix restores the session
from it, so **no new sign-on is needed after a restart**. The browser SSO flow
only has to be repeated if the server revokes the token (token expiry, password
change, device logout); in that case the stored token is removed
automatically and the SSO flow is started again on the next (auto)connect.

A hsignal is sent out when the SSO helper spawns as well, the name of the
hsignal is `matrix_sso_login` and it will contain the name of the server in the
`server` variable and the full URL that can be used to log in in the `url`
variable.

To open the login URL automatically in a browser a trigger can be added:

        /trigger add sso_browser hsignal matrix_sso_login "" "" "/exec -bg firefox ${url}"

If signing on on the same host as Weechat is undesirable the listening port of
the SSO helper should be set to a static value using the
`sso_helper_listening_port` setting:

       /set matrix.server.myserver.sso_helper_listening_port 8443

After setting the listening port the same port on the local machine can be
forwarded using ssh to the remote host:

        ssh -L 8443:localhost:8443 example.org

This forwards the local port 8443 to the localhost:8443 address on example.org.
Note that it is necessary to forward the port to the localhost address on the
remote host because the helper only listens on localhost.

## Cross-signing

Current clients such as Element only trust a device that is signed with the
account's cross-signing key, and they offer no way to verify another session
from their side. weechat-matrix can't do full cross-signing, but it can sign
its own device if the account uses server side secret storage (Element calls
it "Recovery" or "Secure Backup"):

        /olm cross-sign <recovery key>

Instead of typing the recovery key, it can be stored in WeeChat's secured
data once and the key argument left out (this also applies to
`/olm backup restore`):

        /secure set matrix_recovery_key <recovery key>
        /olm cross-sign

The command has to be run in a matrix buffer. It needs the helper script
[contrib/matrix_cross_sign](contrib/matrix_cross_sign.py) installed under your
`PATH` as `matrix_cross_sign` (without the `.py` suffix); it only needs the
`cryptography` package, which is already a dependency of `pyOpenSSL`. The
helper unlocks the self-signing key with the recovery key, checks it against
the key published for the account, checks that the device keys stored on the
server are the local ones, signs them and uploads the signature. The recovery
key and the access token are passed to it on stdin and are not stored.

If the server lost the keys of this device (seen after a device got
recreated on a re-login) they are uploaded again automatically, after that
the command can be repeated.

## Key backup

Messages that were encrypted before this device existed (or while no keys
were shared with it) can be unlocked with the room keys from the server side
key backup that Element keeps:

        /olm backup restore [<recovery key>]

The backup key is unlocked with the recovery key (via
`matrix_cross_sign`, same requirements as above), all backed up room keys are
downloaded, decrypted and imported, and messages already shown as
undecryptable are decrypted again. Older history can then be fetched as
usual. The restore is one-shot: new keys are not uploaded to the backup.

## Unverified devices of other users

By default weechat-matrix refuses to send into an encrypted room while any
device in it is neither verified, ignored nor blacklisted ("Untrusted devices
found in room"). `/olm ignore <user-id> *` marks all current devices of a user
as ignored, which here means "encrypt for it without asking", not "hide the
user". To get Element's behaviour for all current and future devices of
other users:

        /set matrix.network.auto_ignore_new_devices on

Devices of your own account are never ignored automatically; verify or
blacklist them with `/olm`.

`/olm verification start|accept|cancel|confirm` uses the
`m.key.verification.request` flow since v0.3.2, which current clients expect
for emoji (SAS) verification.

## Bar items

There are two bar items provided by this script:

1. `matrix_typing_notice` - shows the currently typing users

1. `matrix_modes` - shows room and server info (encryption status of the room,
   server connection status)

They can be added to the weechat status bar as usual:
       /set weechat.bar.status.items

The `matrix_modes` bar item is replicated in the already used `buffer_modes` bar
item.

## Typing notifications and read receipts

The sending of typing notifications and read receipts can be temporarily
disabled for a given room via the `/room` command. They can also be permanently
configured using standard weechat conditions settings with the following
settings:

1. `matrix.network.read_markers_conditions`
1. `matrix.network.typing_notice_conditions`

## Cursor bindings

While you can reply on a matrix message using the `/reply-matrix` command (see
its help in weechat), weechat-matrix also adds a binding in `/cursor` mode to
easily reply to a particular message. This mode can be triggered either by
running `/cursor`, or by middle-clicking somewhere on the screen. See weechat's
help for `/cursor`.

The default binding is:

    /key bindctxt cursor @chat(python.matrix.*):r hsignal:matrix_cursor_reply

This means that you can reply to a message in a Matrix buffer using the middle
mouse button, then `r`.

This binding is automatically set when the script is loaded and there is no
such binding yet. If you want to use a different key than `r`, you can execute
the above command with a different key in place of `r`. To use modifier keys
like control and alt, use alt-k, then your wanted binding key combo, to enter
weechat's representation of that key combo in the input bar.

## Navigating room buffers using go.py

If you try to use the `go.py` script to navigate buffers created by
weechat-matrix, `go.py` will by default use the full buffer name which does not
contain a human-readable room display name but only the Matrix room ID. This is
necessary so that the logger file is able to produce unique, permanent
filenames for a room.

However, buffers also have human-readable short names. To make `go.py` use the
short names for navigation, you can run the following command:

```
/set plugins.var.python.go.short_name "on"
```

As an alternative, you can also force weechat-matrix to use human-readable
names as the full buffer names by running

```
/set matrix.look.human_buffer_names on
```

Beware that you will then also need to adjust your logger setup to prevent room
name conflicts from causing logger file conflicts.

# Helpful Commands

`/help matrix` will print information about the `/matrix` command.

`/help olm` will print information about the `/olm` command that is used for
device verification.

`/matrix help [command]` will print information for subcommands, such as `/matrix help server`

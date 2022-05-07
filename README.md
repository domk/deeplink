# deeplink
Create links to simulate a specific directory

## Use case
You have an issue with an application that relies haevily on your `$HOME` directory files. Unfortunalty the potential culprits are many. You would like to remove most of the files to find out where is the problem. But as it's your `$HOME` directory this will mess up your login setup.

Deeplink creates for you another directory hosting all your `$HOME`files as links.

```shell
$ cd $HOME
$ deeplink -s . ./some_path/simulated_home
```

The result of the command is that both `$HOME` and `$HOME/some_path/simulated_home` contain the same files and directories although the later contains only links to original ones and that `$HOME/some_path/simulated_home` does not contain a link to `./some_path/simulated_home`. In other words, `$HOME/some_path/simulated_home/some_path` exists but not `$HOME/some_path/simulated_home/some_path/simulated_home`.

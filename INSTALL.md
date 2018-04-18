# Idea

`pylexibank` supports the idea of having [lexibank data sets](https://github.com/lexibank) as Python packages. This allows for an easy management of data sets by facilitating Python's (and `pip`'s) capabilities for installing and managing Python modules.

# Requirements

* Python
* support for virtual environments (i.e. a working `virtualenv` command)
* `pip`
* `git`

# Installation

Start by preparing your working environment:
```
mkdir lexibank-working
cd lexibank-working
virtualenv venv
source venv/bin/activate
```

Your command prompt should now show `(venv)` before all your commands; this means that the virtual environment is ready and in use (if, at any time, you'd like to leave the virtual environment, just type `deactivate`).

Let's continue by installing the necessary requirements (everything still happens in the `lexibank-working` directory with the previously activated virtual environment):

```
pip install pylexibank
git clone https://github.com/clld/glottolog
git clone https://github.com/clld/concepticon-data
```

Note that the previous three commands are only required once per virtual environment. They are not required when installing new data sets (see below).

Now we can perform the initial setup of `pylexibank`, which needs to know where the local Glottolog and Concepticon data can be found:

```
lexibank
```

You should see:

```
Welcome to lexibank!

You seem to be running lexibank for the first time.
Your system configuration will now be written to a config file to be used
whenever lexibank is run lateron.

You need a local clone or release of (a fork of) https://github.com/clld/glottolog
Local path to clld/glottolog: 
```

Since you should still be in the `lexibank-working` directory and since we freshly cloned the Glottolog and Concepticon data into this directory, just type:

```
Local path to clld/glottolog: glottolog
```

And for the next prompt:

```
Local path to clld/concepticon-data: concepticon-data
```

If all went well, a short message about the configuration file and its location should appear. Don't be confused by any 'errors' (i.e. 'error: the following arguments are required ...', this is just `pylexibank` urgently wanting to begin its work.)

Now we have performed the initial setup and can begin working with data sets. Let's get two of them:

```
git clone https://github.com/lexibank/birchallchapacuran
git clone https://github.com/lexibank/allenbai
```

Thanks to these just being Python packages, installation is straightforward:

```
pip install -e allenbai/
pip install -e birchallchapacuran/
```

That's it! `lexibank ls` should show that the two data sets have been installed successfully:

```
lexibank ls
ID                  Title
------------------  ----------------------------------------
allenbai            Bai Dialect Survey
birchallchapacuran  A Combined Comparative and Phylogenetic…
zztotal             2

```

Now you're all set. For example, start working with the data by using the interactive REPL available with `lexibank curate` (note that TAB provides auto completion/command hints):

```
lexibank curate
lexibank-curator> analyze allenbai
lexibank-curator> download allenbai
```

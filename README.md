# Disclaimer

The code in this repo isn't perfect. It works well enough for me but
use at your own risk. I was experimenting with an AI driven development
process with my customized neovim. Basically, the idea is to take
per-package Clear Linux optimizations and translate them into Gentoo's
`/etc/portage/package.env` overrides.

High level usage overview is:

1. Run `clone_clearlinux_repos.py` to make a shallow clone of the Clear
   Linux repos that have been mapped to Gentoo packages. It does a
   sparse checkout of each repo, since the `options.conf` file is all
   the scripts care about.
2. Run `options_parser.py` to create the `package.env` overrides
   from the `options.conf` files in all the cloned repos.

These are the steps needed to update the package mapping:

1. Use `fetch_clearlinux_pkgs.py` to grab the list of Clear Linux
   packages. Will take a while, there are enough repos that you'll hit a
   rate limit.
2. Use `get_gentoo_pkgs.py` to grab the list of Gentoo packages (will need to
   run on Gentoo).
3. Run `save_mapping.py` to create a JSON mapping of Clear Linux packages to
   Gentoo packages.

If this project became serious (as in, gained enough of a following /
support), there's a strong possibility I'd end up rewriting the whole
thing from scratch. I have a much better idea of the problem space and
I'd do a lot of things differently. It was a good learning experience
all the same.

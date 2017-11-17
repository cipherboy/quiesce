import numpy as np
from gameanalysis import rsgame


def deviation_payoffs(prof_sched, game, mix, num, *, boots=0, chunk_size=None):
    """Bootstrap deviation payoffs

    Parameters
    ----------
    prof_sched : Scheduler
        The scheduler to sample profiles from.
    game : RsGame
        The game defining what's sampled.
    mix : ndarray
        The mixture to calculate the regret of.
    num : int
        The number of samples to gather. Must be positive.
    boots : int, optional
        The number of bootstrap samples to take. The accuracy of bootstrap is
        independent of this number, but more will reduce the variance of the
        underlying confidence bounds. The default will compute no bootstrap
        gains.
    chunk_size : int, optional
        An implementation detail specifying how frequently profiles are
        scheduled since this algorithm inherently operates in a streaming
        manner. Ideally this number should be set such that the time to
        schedule and process chunk_size roughly equals the time for one
        simulation. It also controls how much memory this uses. By default this
        is set to ten times the number of bootstraps, or 1000 if no bootstraps
        are requested.

    Notes
    -----
    This uses memory on the order of `boots + chunk_size`. It is inefficient if
    `num` is less than boots.

    Returns
    -------
    mean_gains : ndarray (num_strats,)
        The mean deviation payoffs from the mixture.
    boot_gains : ndarray (boots, num_strats)
        The deviation payoffs for each bootstrap sample.
    """
    assert num > 0, "can't schedule zero samples"
    chunk_size = chunk_size or boots * 10 or 1000
    game = rsgame.emptygame_copy(game)
    profiles = _chunk_profiles(prof_sched, game, mix, num, chunk_size)
    devs = np.empty(game.num_strats)
    mean_devs = np.zeros(game.num_strats)
    boot_devs = np.zeros((boots, game.num_strats))
    remaining = np.empty(boots, int)
    remaining.fill(num)
    for i in range(num):
        for j in range(game.num_strats):
            devs[j] = next(profiles)[j]
        mean_devs += (devs - mean_devs) / (i + 1)
        samps = np.random.binomial(remaining, 1 / (num - i))
        remaining -= samps
        boot_devs += samps[:, None] * devs / num

    return mean_devs, boot_devs


def _chunk_profiles(sched, game, mix, num, chunk_size):
    """Return a generator over payoffs that schedules somewhat efficiently"""
    proms = []
    while 0 < num:
        new_profs = game.random_deviator_profiles(
            mix, min(num, chunk_size)).reshape((-1, game.num_strats))
        num -= chunk_size
        new_proms = [sched.schedule(prof) for prof in new_profs]
        for prom in proms:
            yield prom.get()
        proms = new_proms
    for prom in proms:  # pragma: no branch
        yield prom.get()

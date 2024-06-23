import pandas as pd
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt
import time
from collections import OrderedDict
from sklearn.calibration import calibration_curve
from sklearn.calibration import CalibrationDisplay


class ELO:
    def __init__(
        self,
        winners,
        losers,
        ids=None,
        timestamps=None,
        k=20,
        elo_init=1500,
        elo_diff=400,
        seasonal_mean_reversion=0,
    ):
        self.k = k
        self.elo_init = elo_init
        self.elo_diff = elo_diff

        winners = list(winners)
        losers = list(losers)

        ELO.__check_valid_games__(winners, losers, ids, timestamps)
        ELO.__check_valid_params__(k, elo_init, elo_diff, seasonal_mean_reversion)

        # Assemble temporary empty dataframe to store ELOs
        if ids is None:
            self.ids = range(len(winners))
        else:
            self.ids = ids
        self.winners = winners
        self.losers = losers
        self.competitors = sorted(list(set(winners) | set(losers)))
        self.timestamps = timestamps
        self.seasonal_mean_reversion = seasonal_mean_reversion
        if self.timestamps is not None:
            # sort arrays by timestamp
            self.ids, self.winners, self.losers, self.timestamps = zip(
                *sorted(
                    zip(self.ids, self.winners, self.losers, self.timestamps),
                    key=lambda x: x[3],
                )
            )

    # Compute the ELO of every competitor after each match (37s original)
    # 0.04476022720336914s (without dataframe conversion)
    # 0.15063881874084473 (with dataframe conversion)
    def fit_fastest(self):
        start = time.time()
        elo_dict = OrderedDict(
            [(competitor, self.elo_init) for competitor in self.competitors]
        )
        game_array = np.vstack([self.ids, self.winners, self.losers, self.timestamps]).T
        elo_array = [np.ones(len(self.competitors)) * self.elo_init]
        game_probs, winner_prev_elo, loser_prev_elo = [], [], []
        current_year = self.timestamps[0].year if self.timestamps is not None else None
        for i, game in enumerate(game_array):
            game_id, winner, loser, timestamp = game
            if self.timestamps is not None and timestamp.year != current_year:
                current_year = timestamp.year
                mean_elo = np.mean(elo_array[-1])
                elo_dict = {
                    team: mean_elo
                    + (1 - self.seasonal_mean_reversion) * (elo - mean_elo)
                    for team, elo in elo_dict.items()
                }
            winner_elo, loser_elo = elo_dict[winner], elo_dict[loser]
            winner_new_elo, loser_new_elo, expected_outcome_prob = (
                ELO.compute_pairwise_elo(
                    winner_elo, loser_elo, elo_diff=self.elo_diff, k=self.k
                )
            )
            game_probs.append(expected_outcome_prob)
            elo_dict[winner], elo_dict[loser] = winner_new_elo, loser_new_elo
            elo_array.append(list(elo_dict.values()))
        self.elo_df = pd.concat(
            [
                pd.DataFrame(
                    np.vstack(
                        [
                            self.ids,
                            self.timestamps,
                            self.winners,
                            self.losers,
                            game_probs,
                        ]
                    ).T,
                    columns=["id", "timestamp", "winner", "loser", "win_prob"],
                ).set_index("id"),
                pd.DataFrame(elo_array[1:], columns=self.competitors, index=self.ids),
            ],
            axis=1,
        )
        print("Computed elos in", time.time() - start, "seconds.")

    # Show a calibration curve of the ELO output probabilities after fitting
    def show_calibration(self, start_year=2018, A=5, B=0.2):
        d = self.elo_df.loc[self.elo_df.timestamp > str(start_year)]
        win_sample = d.sample(frac=0.5)
        lose_sample = d.drop(win_sample.index)
        p_true = [1] * len(win_sample) + [0] * len(lose_sample)
        p_pred = win_sample.win_prob.tolist() + (1 - lose_sample.win_prob).tolist()
        p_pred = np.array(p_pred)

        def sigmoid(x, A, B):
            return 1 / (1 + np.exp(A * x + B))

        def invsigmoid(x, A, B=1 / 2):
            return -(1 / A) * np.log((1 + B) / (x + B / 2) - 1) + 1 / 2

        prob_true, prob_pred = calibration_curve(
            p_true, invsigmoid(p_pred, A, B), n_bins=20, strategy="uniform"
        )
        # prob_true, prob_pred = calibration_curve(p_true, p_pred, n_bins=20, strategy='uniform')
        plt.figure(dpi=300)
        CalibrationDisplay(prob_true, prob_pred, p_pred).plot()
        plt.suptitle("Calibration Curve with Inverse Sigmoid")
        plt.title(
            f"A={A}, B={B}, start_year={start_year}, k={self.k}, elo_init={self.elo_init}, elo_diff={self.elo_diff}, smr={self.seasonal_mean_reversion}"
        )
        plt.grid()

    @staticmethod
    def compute_pairwise_elo(winner_elo, loser_elo, elo_diff, k):
        expected_outcome_prob = ELO.compute_expected_outcome_prob(
            winner_elo, loser_elo, elo_diff=elo_diff
        )
        return (
            winner_elo + k * (1 - expected_outcome_prob),
            loser_elo - k * (1 - expected_outcome_prob),
            expected_outcome_prob,
        )

    @staticmethod
    def compute_expected_outcome_prob(elo1, elo2, elo_diff=400):
        return 1 / (1 + 10 ** ((elo2 - elo1) / elo_diff))

    @staticmethod
    def __check_valid_params__(k, elo_init, elo_diff, seasonal_mean_reversion):
        assert isinstance(k, int) and k > 0
        assert isinstance(elo_init, int) and elo_init > 0
        assert isinstance(elo_diff, int) and elo_diff > 0
        assert (
            isinstance(seasonal_mean_reversion, float) and seasonal_mean_reversion <= 1
        )

    @staticmethod
    def __check_valid_games__(winners, losers, ids, timestamps):
        # assert proper data types
        assert pd.api.types.is_list_like(winners)
        assert pd.api.types.is_list_like(losers)
        assert ids is None or pd.api.types.is_list_like(ids)
        assert timestamps is None or pd.api.types.is_list_like(timestamps)

        # check that winners, losers, ids, and timestamps have the same length
        assert len(winners) == len(losers)
        assert ids is None or len(ids) == len(winners)
        assert timestamps is None or len(timestamps) == len(winners)

        # check that all ids are unique
        assert ids is None or len(set(ids)) == len(ids)

        # check that no teams play against themselves
        for i in range(len(winners)):
            assert winners[i] != losers[i]

        # check that the timestamps are valid
        if timestamps is not None:
            for timestamp in timestamps:
                try:
                    pd.to_datetime(timestamp)
                except ValueError:
                    raise ValueError("Invalid timestamp: {}".format(timestamp))

    def show_elos(self, since=None):
        if since is not None:
            return self.elo_df.loc[self.elo_df.timestamp >= str(since)]
        return self.elo_df

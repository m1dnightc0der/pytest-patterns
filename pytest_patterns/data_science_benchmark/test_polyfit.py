import numpy as np

import pytest
from pytest_cases import cases_fixture
from pytest_harvest.results_bags import ResultsBag

from .challengers_polyfit import PolyFitChallenger
from . import datasets_polyfit


# ------------ The two challengers ----------
@pytest.fixture(params=[1, 2], ids="polyfit(degree={})".format)
def challenger(request):
    """
    A fixture creating the two challengers
    """
    return PolyFitChallenger(degree=request.param)


# ------------- To collect datasets ------------
@cases_fixture(module=datasets_polyfit, scope='session')
def dataset(case_data):
    """
    A fixture collecting all 'cases' (datasets) in `datasets_polyfit`.

    Note: we use "scope=session" so that this method is called only once per case.
    This ensures that each file is read once. We could reach the same result by using
    lru_cache in the case function, but since we have several case functions it would
    be more cumbersome to do.
    """
    # get the dataset
    x, y = case_data.get()
    return x, y


# ------------- To evaluate the algorithms ------------
def test_poly_fit(challenger, dataset, results_bag):
    """
    Tests the polyfit function with `degree` on the provided `dataset`,
    and stores the model accuracy (cv-rmse) in the results_bag
    """

    # Get the test case at hand
    x, y = dataset

    # Fit the model
    challenger.fit(x, y)
    results_bag.model = challenger

    # Use the model to perform predictions
    predictions = challenger.predict(x)

    # Evaluate the prediction error
    cvrmse = np.sqrt(np.mean((predictions-y)**2)) / np.mean(y)
    print("Relative error (cv-rmse) is: %.2f%%" % (cvrmse * 100))
    results_bag.cvrmse = cvrmse


# To make sure that the benchmark is not biased by import times on the first run, we perform a first run here
test_poly_fit(PolyFitChallenger(degree=1), (np.arange(10), np.arange(10)), ResultsBag())


# ------------- To create the final benchmark table ------------
def test_synthesis(module_results_df):
    """
    Creates the benchmark synthesis table
    Note: we could do this at many other places (hook, teardown of a session-scope fixture...)
    as explained in `pytest-harvest` plugin
    """
    # ----------- (1) `module_results_df` contains the raw (12 rows) table -----------
    # rename columns and only keep useful information
    module_results_df = module_results_df.rename(columns={'challenger_param': 'degree', 'dataset_param': 'dataset'})
    module_results_df['challenger'] = module_results_df['model'].map(str)  # only keep the string representation
    module_results_df = module_results_df[['dataset', 'challenger', 'degree', 'status', 'duration_ms', 'cvrmse']]

    # write to csv
    module_results_df.to_csv("polyfit_bench_results.csv", sep=';', decimal=',')

    # pretty-print (requires tabulate)
    try:
        from tabulate import tabulate
        print("\n" + tabulate(module_results_df, headers='keys', tablefmt='pipe'))
    except ImportError:
        pass

    # ----------- (2) graphical synthesis: bar chart (requires matplotlib)------------
    try:
        import matplotlib.pyplot as plt

        # convert all to categorical so that we can pivot
        module_results_df = module_results_df.apply(lambda s: s.astype("category") if s.dtype == 'object' else s)

        cvrmse_df = module_results_df[['dataset', 'challenger', 'cvrmse']].pivot(index='dataset',
                                                                                 columns='challenger',
                                                                                 values='cvrmse')

        ax = cvrmse_df.plot.bar()
        ax.set_ylabel("cvrmse")
        plt.xticks(plt.xticks()[0], plt.xticks()[1], rotation=30, ha='right')
        plt.subplots_adjust(left=0.20, bottom=0.25)
        print("Close the plots to continue...")
        plt.show()
    except ImportError:
        pass

    # ----------- (3) summarizing the results further - by challenger --------------
    summary_df = module_results_df[['degree', 'duration_ms', 'cvrmse']].groupby('degree', axis=0).agg({
        'duration_ms': ['mean', 'std'],
        'cvrmse': ['mean', 'std']
    })
    # pretty-print (requires tabulate)
    try:
        print("\n" + tabulate(summary_df, headers='keys'))
    except NameError:
        pass

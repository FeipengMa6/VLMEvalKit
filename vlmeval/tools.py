import sys
from vlmeval.config import *
from vlmeval.smp import *

# Define valid modes
MODES = ('dlist', 'mlist', 'missing', 'circular', 'localize', 'check', 'run')

CLI_HELP_MSG = \
    f"""
    Arguments received: {str(['vlmutil'] + sys.argv[1:])}. vlmutil commands use the following syntax:

        vlmutil MODE MODE_ARGS

        Where   MODE (required) is one of {MODES}
                MODE_ARG (optional) is the argument for specific mode

    Some usages for xtuner commands: (See more by using -h for specific command!)

        1. List all the dataset by levels: l1, l2, l3, etc.:
            vlmutil dlist [l1/l2/l3/...]
        2. List all the models by categories: 4.33.0, 4.37.0, api, etc.:
            vlmutil mlist 4.33.0 [all/small/large]
        3. Report missing results:
            vlmutil missing [l1/l2/l3/...]
        4. Create circular questions (only for multiple-choice questions with no more than 4 choices):
            vlmutil circular input.tsv
        5. Create a localized version of the dataset (for very large tsv files):
            vlmutil localize input.tsv
        6. Check the validity of a model:
            vlmutil check [model_name/model_series]
        7. Run evaluation for missing results:
            vlmutil run l2 hf

    GitHub: https://github.com/open-compass/VLMEvalKit
    """  # noqa: E501


dataset_levels = {
    'l1': [
        ('MMVet', 'gpt-4-turbo_score.csv'), ('MMMU_DEV_VAL', 'acc.csv'),
        ('MathVista_MINI', 'gpt-4-turbo_score.csv'), ('HallusionBench', 'score.csv'),
        ('OCRBench', 'score.json'), ('AI2D_TEST', 'acc.csv'), ('MMStar', 'acc.csv'),
        ('MMBench_V11', 'acc.csv'), ('MMBench_CN_V11', 'acc.csv')
    ],
    'l2': [
        ('MME', 'score.csv'), ('LLaVABench', 'score.csv'), ('RealWorldQA', 'acc.csv'),
        ('MMBench', 'acc.csv'), ('MMBench_CN', 'acc.csv'), ('CCBench', 'acc.csv'),
        ('SEEDBench_IMG', 'acc.csv'), ('COCO_VAL', 'score.json'), ('POPE', 'score.csv'),
        ('ScienceQA_VAL', 'acc.csv'), ('ScienceQA_TEST', 'acc.csv'),
    ],
    'l3': [
        ('OCRVQA_TESTCORE', 'acc.csv'), ('TextVQA_VAL', 'acc.csv'),
        ('ChartQA_TEST', 'acc.csv'), ('DocVQA_VAL', 'acc.csv'), ('InfoVQA_VAL', 'acc.csv'),
        ('SEEDBench2_Plus', 'acc.csv')
    ]
}

dataset_levels['l12'] = dataset_levels['l1'] + dataset_levels['l2']
dataset_levels['l23'] = dataset_levels['l2'] + dataset_levels['l3']
dataset_levels['l123'] = dataset_levels['l12'] + dataset_levels['l3']

models = {
    '4.33.0': list(qwen_series) + list(internvl_series) + list(xcomposer_series) + [
        'mPLUG-Owl2', 'flamingov2', 'VisualGLM_6b', 'MMAlaya', 'PandaGPT_13B', 'VXVERSE'
    ] + list(idefics_series) + list(minigpt4_series) + list(instructblip_series),
    '4.37.0': [x for x in llava_series if 'next' not in x] + [
        'TransCore_M', 'cogvlm-chat', 'cogvlm-grounding-generalist', 'emu2_chat',
        'MiniCPM-V', 'MiniCPM-V-2', 'OmniLMM_12B', 'InternVL-Chat-V1-5'
    ] + list(xtuner_series) + list(yivl_series) + list(deepseekvl_series),
    'latest': [
        'idefics2_8b', 'Bunny-llama3-8B', 'MiniCPM-Llama3-V-2_5', '360VL-70B', 'paligemma-3b-mix-448'
    ] + [x for x in llava_series if 'next' in x],
    'api': list(api_models)
}

SKIP_MODELS = [
    'InternVL-Chat-V1-1', 'InternVL-Chat-V1-2', 'InternVL-Chat-V1-2-Plus',
    'MiniGPT-4-v1-13B', 'instructblip_13b', 'MGM_7B', 'GPT4V_HIGH',
]

LARGE_MODELS = [
    'InternVL-Chat-V1-2', 'InternVL-Chat-V1-2-Plus', 'idefics_80b_instruct',
    '360VL-70B', 'emu2_chat'
]


def completed(m, d, suf):
    score_file = f'{m}/{m}_{d}_{suf}'
    if osp.exists(score_file):
        return True
    if d == 'MMBench':
        s1, s2 = f'{m}/{m}_MMBench_DEV_EN_{suf}', f'{m}/{m}_MMBench_TEST_EN_{suf}'
        return osp.exists(s1) and osp.exists(s2)
    elif d == 'MMBench_CN':
        s1, s2 = f'{m}/{m}_MMBench_DEV_CN_{suf}', f'{m}/{m}_MMBench_TEST_CN_{suf}'
        return osp.exists(s1) and osp.exists(s2)
    return False


def DLIST(lvl):
    lst = [x[0] for x in dataset_levels[lvl]]
    return lst


def MLIST(lvl, size='all'):
    model_list = models[lvl]
    if size == 'small':
        model_list = [m for m in model_list if m not in LARGE_MODELS]
    elif size == 'large':
        model_list = [m for m in model_list if m in LARGE_MODELS]
    return [x[0] for x in model_list]


def MISSING(lvl):
    from vlmeval.config import supported_VLM
    models = list(supported_VLM)
    models = [m for m in models if m not in SKIP_MODELS and osp.exists(m)]
    if lvl in dataset_levels.keys():
        data_list = dataset_levels[lvl]
    else:
        data_list = [(D, suff) for (D, suff) in dataset_levels['l123'] if D == lvl]
    missing_list = []
    for f in models:
        for D, suff in data_list:
            if not completed(f, D, suff):
                missing_list.append((f, D))
    return missing_list


def CIRCULAR(inp):
    assert inp.endswith('.tsv')
    data = load(inp)
    OFFSET = 1e6
    while max(data['index']) >= OFFSET:
        OFFSET *= 10

    assert 'E' not in data, 'Currently build_circular only works for up to 4-choice questions'
    data_2c = data[pd.isna(data['C'])]
    data_3c = data[~pd.isna(data['C']) & pd.isna(data['D'])]
    data_4c = data[~pd.isna(data['D'])]
    map_2c = [('AB', 'BA')]
    map_3c = [('ABC', 'BCA'), ('ABC', 'CAB')]
    map_4c = [('ABCD', 'BCDA'), ('ABCD', 'CDAB'), ('ABCD', 'DABC')]

    def okn(o, n=4):
        ostr = o.replace(',', ' ')
        osplits = ostr.split()
        if sum([c in osplits for c in string.ascii_uppercase[:n - 1]]) == n - 1:
            return False
        olower = o.lower()
        olower = olower.replace(',', ' ')
        olower_splits = olower.split()
        if 'all' in olower_splits or 'none' in olower_splits:
            return False
        return True

    yay4, nay4 = [], []
    lt4 = len(data_4c)
    for i in range(lt4):
        if okn(data_4c.iloc[i]['D'], 4):
            yay4.append(i)
        else:
            nay4.append(i)
    data_4c_y = data_4c.iloc[yay4]
    data_4c_n = data_4c.iloc[nay4]
    data_3c = pd.concat([data_4c_n, data_3c])

    yay3, nay3 = [], []
    lt3 = len(data_3c)
    for i in range(lt3):
        if okn(data_3c.iloc[i]['C'], 3):
            yay3.append(i)
        else:
            nay3.append(i)
    data_3c_y = data_3c.iloc[yay3]
    data_3c_n = data_3c.iloc[nay3]
    data_2c = pd.concat([data_3c_n, data_2c])

    def remap(data_in, tup, off):
        off = int(off)
        data = data_in.copy()
        char_map = {k: v for k, v in zip(*tup)}
        idx = data.pop('index')
        answer = data.pop('answer')
        answer_new = [char_map[x] if x in char_map else x for x in answer]
        data['answer'] = answer_new
        options = {}
        for c in char_map:
            options[char_map[c]] = data.pop(c)
        for c in options:
            data[c] = options[c]
        data.pop('image')
        data['image'] = idx
        idx = [x + off for x in idx]
        data['index'] = idx
        return data

    data_all = pd.concat([
        data_2c,
        data_3c_y,
        data_4c_y,
        remap(data_2c, map_2c[0], OFFSET),
        remap(data_3c_y, map_3c[0], OFFSET),
        remap(data_4c_y, map_4c[0], OFFSET),
        remap(data_3c_y, map_3c[1], OFFSET * 2),
        remap(data_4c_y, map_4c[1], OFFSET * 2),
        remap(data_4c_y, map_4c[2], OFFSET * 3),
    ])

    tgt_file = inp.replace('.tsv', '_CIRC.tsv')
    dump(data_all, tgt_file)
    print(f'The circularized data is saved to {tgt_file}')
    assert osp.exists(tgt_file)
    print(f'The MD5 for the circularized data is {md5(tgt_file)}')


PTH = osp.realpath(__file__)
IMAGE_PTH = osp.join(osp.dirname(PTH), '../assets/apple.jpg')

msg1 = [
    IMAGE_PTH,
    'What is in this image?'
]
msg2 = [
    dict(type='image', value=IMAGE_PTH),
    dict(type='text', value='What is in this image?')
]
msg3 = [
    IMAGE_PTH,
    IMAGE_PTH,
    'How many apples are there in these images?'
]
msg4 = [
    dict(type='image', value=IMAGE_PTH),
    dict(type='image', value=IMAGE_PTH),
    dict(type='text', value='How many apples are there in these images?')
]


def CHECK(val):
    if val in supported_VLM:
        model = supported_VLM[val]()
        print(f'Model: {val}')
        for i, msg in enumerate([msg1, msg2, msg3, msg4]):
            if i > 1 and not model.INTERLEAVE:
                continue
            res = model.generate(msg)
            print(f'Test {i + 1}: {res}')
    elif val in models:
        model_list = models[val]
        for m in model_list:
            CHECK(m)


def decode_img(tup):
    im, p = tup
    if osp.exists(p):
        return
    decode_base64_to_image_file(im, p)


def LOCALIZE(fname):
    base_name = osp.basename(fname)
    dname = osp.splitext(base_name)[0]
    data = load(fname)
    new_fname = fname.replace('.tsv', '_local.tsv')

    indices = list(data['index'])
    images = list(data['image'])
    root = LMUDataRoot()
    root = osp.join(root, 'images', dname)
    os.makedirs(root, exist_ok=True)

    img_paths = [osp.join(root, f'{idx}.jpg') for idx in indices]
    tups = [(im, p) for p, im in zip(img_paths, images)]

    pool = mp.Pool(32)
    pool.map(decode_img, tups)
    pool.close()
    data.pop('image')
    data['image_path'] = img_paths
    dump(data, new_fname)
    print(f'The localized version of data file is {new_fname}')


def RUN(lvl, model):
    import torch
    NGPU = torch.cuda.device_count()
    SCRIPT = osp.join(osp.dirname(__file__), '../run.py')
    logger = get_logger('Run Missing')

    def get_env(name):
        assert name in ['433', '437', 'latest']
        load_env()
        env_key = f'ENV_{name}'
        return os.environ.get(env_key, None)

    missing = MISSING(lvl)
    if model == 'all':
        pass
    elif model == 'hf':
        missing = [x for x in missing if x[0] not in models['api']]
    elif model in models:
        missing = [x for x in missing if x[0] in models[missing]]
    elif model in supported_VLM:
        missing = [x for x in missing if x[0] == model]

    missing.sort(key=lambda x: x[0])
    groups = defaultdict(list)
    for m, D in missing:
        groups[m].append(D)
    for m in groups:
        datasets = ' '.join(groups[m])
        logger.info(f'Running {m} on {datasets}')
        exe = 'python' if m in LARGE_MODELS or m in models['api'] else 'torchrun'
        if m not in models['api']:
            env = '433'
            env = '437' if m in models['4.37.0'] else env
            env = 'latest' if m in models['latest'] else env
            pth = get_env(env)
            if pth is not None:
                exe = osp.join(pth, 'bin', exe)
            else:
                logger.warning(f'Cannot find the env path {env} for model {m}')
        if exe.endswith('torchrun'):
            cmd = f'{exe} --nproc-per-node={NGPU} {SCRIPT} --model {m} --data {datasets}'
        elif exe.endswith('python'):
            cmd = f'{exe} {SCRIPT} --model {m} --data {datasets}'
        os.system(cmd)


def cli():
    logger = get_logger('VLMEvalKit Tools')
    args = sys.argv[1:]
    if not args:  # no arguments passed
        logger.info(CLI_HELP_MSG)
        return
    if args[0].lower() in MODES:
        if args[0].lower() == 'dlist':
            assert len(args) >= 2
            lst = DLIST(args[1])
            print(' '.join(lst))
        elif args[0].lower() == 'mlist':
            assert len(args) >= 2
            size = 'all'
            if len(args) > 2:
                size = args[2].lower()
            lst = MLIST(args[1], size)
            print(' '.join(lst))
        elif args[0].lower() == 'missing':
            assert len(args) >= 2
            missing_list = MISSING(args[1])
            logger = get_logger('Find Missing')
            logger.info(colored(f'Level {args[1]} Missing Results: ', 'red'))
            for m, D in missing_list:
                logger.info(colored(f'Model {m}, Dataset {D}', 'red'))
        elif args[0].lower() == 'circular':
            assert len(args) >= 2
            CIRCULAR(args[1])
        elif args[0].lower() == 'localize':
            assert len(args) >= 2
            LOCALIZE(args[1])
        elif args[0].lower() == 'check':
            assert len(args) >= 2
            model_list = args[1:]
            for m in model_list:
                CHECK(m)
        elif args[0].lower() == 'run':
            assert len(args) >= 2
            lvl = args[1]
            model = args[2] if len(args) > 2 else 'all'
            RUN(lvl, model)
    else:
        logger.error('WARNING: command error!')
        logger.info(CLI_HELP_MSG)
        return
